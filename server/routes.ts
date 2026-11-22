import crypto from 'node:crypto'
import express from 'express'
import type { Response } from 'express'
import type {
  AuthorizationContext,
  ClinicalNoteDraft,
  MedicalDocument,
  Patient,
  PersonalNoteDraft,
  PrescriptionDraft,
  PrescriptionDraftLine,
  PrescriptionLine,
  SignedPrescription,
} from './types.ts'
import {
  type AuthenticatedRequest,
  authenticateUser,
  findActiveHospitalAssignment,
  getActiveHospitalAssignments,
  isValidUuid,
  parseBasicAuth,
  requireRoles,
  validateLegitimatePurpose,
  validatePatientObjectAccess,
} from './security.ts'
import { store } from './store.ts'
import {
  formatPersonalNotesWithGemini,
  generateClinicalDraftWithGemini,
} from './gemini.ts'

export const apiRouter = express.Router()

const PATIENT_IDENTITY_STATUSES = new Set([
  'verified',
  'probable',
  'unverified',
  'merged',
])
const APPOINTMENT_STATUSES = new Set([
  'scheduled',
  'checked_in',
  'cancelled',
  'completed',
  'no_show',
])
const ENCOUNTER_STATUSES = new Set([
  'planned',
  'in_progress',
  'completed',
  'cancelled',
])
const SOURCE_TYPES = new Set([
  'conversation',
  'document',
  'doctor_entry',
  'patient_statement',
  'import',
  'ai_draft',
  'prescription',
  'catalogue',
])
const VERIFICATION_STATUSES = new Set([
  'unverified',
  'reviewed',
  'verified',
  'disputed',
])
const ALLERGY_CRITICALITIES = new Set([
  'low',
  'high',
  'unknown',
  'unable_to_assess',
])
const ALLOWED_MIME_TYPES = new Set([
  'application/pdf',
  'image/jpeg',
  'image/png',
  'image/tiff',
])

function getPatientInHospital(
  ctx: AuthorizationContext,
  patientId: string,
  res: Response,
): Patient | null {
  if (!isValidUuid(patientId)) {
    res.status(422).json({ detail: 'Invalid patient_id' })
    return null
  }
  if (!validatePatientObjectAccess(ctx.assignment, patientId)) {
    res
      .status(403)
      .json({ detail: 'No approved patient relationship for this operation' })
    return null
  }
  const patient = store.patients.get(patientId)
  if (!patient || patient.hospital_id !== ctx.hospitalId) {
    res.status(404).json({ detail: 'Patient not found' })
    return null
  }
  return patient
}

function validateEncounterForPatient(
  ctx: AuthorizationContext,
  encounterId: string | null | undefined,
  patientId: string,
  res: Response,
): boolean {
  if (!encounterId) return true
  if (!isValidUuid(encounterId)) {
    res.status(422).json({ detail: 'Invalid encounter_id' })
    return false
  }
  const encounter = store.encounters.get(encounterId)
  if (!encounter || encounter.hospital_id !== ctx.hospitalId) {
    res
      .status(404)
      .json({ detail: 'Encounter not found in the requested hospital' })
    return false
  }
  if (encounter.patient_id !== patientId) {
    res.status(409).json({ detail: 'Encounter does not belong to the patient' })
    return false
  }
  return true
}

function getSafetyWarnings(
  hospitalId: string,
  patientId: string,
  lines: Array<{ medicine_name: string }>,
): string[] {
  const warnings = new Set<string>()
  const names = lines
    .map((line) => line.medicine_name.trim().toLowerCase())
    .filter(Boolean)

  for (const allergy of store.allergies.values()) {
    if (allergy.hospital_id !== hospitalId || allergy.patient_id !== patientId) {
      continue
    }
    const substance = allergy.substance.trim().toLowerCase()
    if (
      substance &&
      names.some((name) => substance.includes(name) || name.includes(substance))
    ) {
      warnings.add(
        `Review possible documented allergy match: ${allergy.substance}`,
      )
    }
  }

  const activeMeds = new Set<string>()
  for (const med of store.medications.values()) {
    if (
      med.hospital_id === hospitalId &&
      med.patient_id === patientId &&
      med.status === 'active'
    ) {
      const normalized = med.medicine_name.trim().toLowerCase()
      if (normalized) activeMeds.add(normalized)
    }
  }

  for (const name of names) {
    if (activeMeds.has(name)) {
      warnings.add(`Review possible duplicate therapy: ${name}`)
    }
  }

  return Array.from(warnings).sort()
}

function buildDraftResponse(
  draft: PrescriptionDraft,
  lines: PrescriptionDraftLine[],
  warnings: string[],
) {
  return {
    ...draft,
    lines: lines.map((line) => ({
      id: line.id,
      catalogue_item_id: line.catalogue_item_id,
      medicine_name: line.medicine_name,
      strength: line.strength,
      dose: line.dose,
      route: line.route,
      frequency: line.frequency,
      duration: line.duration,
      quantity: line.quantity,
      instructions: line.instructions,
    })),
    safety_warnings: warnings,
  }
}

function buildPrescriptionResponse(
  prescription: SignedPrescription,
  lines: PrescriptionLine[],
) {
  return {
    ...prescription,
    lines: lines.map((line) => ({
      id: line.id,
      catalogue_item_id: line.catalogue_item_id,
      medicine_name: line.medicine_name,
      strength: line.strength,
      dose: line.dose,
      route: line.route,
      frequency: line.frequency,
      duration: line.duration,
      quantity: line.quantity,
      instructions: line.instructions,
    })),
  }
}

function getDocumentInHospital(
  ctx: AuthorizationContext,
  documentId: string,
  res: Response,
): MedicalDocument | null {
  if (!isValidUuid(documentId)) {
    res.status(422).json({ detail: 'Invalid document_id' })
    return null
  }
  const doc = store.documents.get(documentId)
  if (!doc || doc.hospital_id !== ctx.hospitalId) {
    res.status(404).json({ detail: 'Document not found' })
    return null
  }
  if (!validatePatientObjectAccess(ctx.assignment, doc.patient_id)) {
    res
      .status(403)
      .json({ detail: 'No approved patient relationship for this operation' })
    return null
  }
  return doc
}

// Health
apiRouter.get('/health', (_req, res) => {
  res.json({ status: 'ok' })
})

// Authentication
apiRouter.post('/auth/login', (req, res) => {
  const { email, password } = req.body ?? {}
  if (typeof email !== 'string' || typeof password !== 'string') {
    res.status(422).json({ detail: 'Email and password are required' })
    return
  }
  const user = authenticateUser(email, password)
  if (!user) {
    res.status(401).json({ detail: 'Invalid email or password' })
    return
  }
  const assignments = getActiveHospitalAssignments(user)
  res.json({
    user_id: user.id,
    email: user.email,
    display_name: user.display_name,
    assignments: assignments.map((assignment) => ({
      hospital_user_id: assignment.id,
      hospital_id: assignment.hospital_id,
      role_code: assignment.role_code,
      relationship_scope: assignment.relationship_scope,
    })),
  })
})

apiRouter.get('/auth/me', (req, res) => {
  const credentials = parseBasicAuth(req)
  if (!credentials) {
    res.setHeader('WWW-Authenticate', 'Basic')
    res.status(401).json({ detail: 'Invalid email or password' })
    return
  }
  const user = authenticateUser(credentials.username, credentials.password)
  if (!user) {
    res.setHeader('WWW-Authenticate', 'Basic')
    res.status(401).json({ detail: 'Invalid email or password' })
    return
  }
  const hospitalId = req.header('x-hospital-id')
  if (!isValidUuid(hospitalId)) {
    res.status(422).json({ detail: 'Valid X-Hospital-Id header is required' })
    return
  }
  const purpose = req.header('x-mediflow-purpose')
  if (!validateLegitimatePurpose(purpose)) {
    res.status(400).json({ detail: 'X-Mediflow-Purpose is required' })
    return
  }
  const assignments = getActiveHospitalAssignments(user)
  const assignment = findActiveHospitalAssignment(assignments, hospitalId)
  if (!assignment) {
    res
      .status(403)
      .json({ detail: 'No active assignment in the requested hospital' })
    return
  }
  res.json({
    user_id: user.id,
    email: user.email,
    display_name: user.display_name,
    assignments: assignments
      .filter((item) => item.hospital_id === hospitalId)
      .map((item) => ({
        hospital_user_id: item.id,
        hospital_id: item.hospital_id,
        role_code: item.role_code,
        relationship_scope: item.relationship_scope,
      })),
  })
})

// Patients
apiRouter.post('/patients', requireRoles('doctor', 'staff'), (req: AuthenticatedRequest, res) => {
  const ctx = req.authContext!
  const {
    synthetic_mrn,
    given_name,
    family_name,
    date_of_birth,
    sex_at_birth = null,
    identity_status = 'unverified',
  } = req.body ?? {}

  if (
    typeof synthetic_mrn !== 'string' ||
    !synthetic_mrn.trim() ||
    typeof given_name !== 'string' ||
    !given_name.trim() ||
    typeof family_name !== 'string' ||
    !family_name.trim() ||
    typeof date_of_birth !== 'string' ||
    !date_of_birth.trim()
  ) {
    res.status(422).json({ detail: 'Missing required patient fields' })
    return
  }
  if (!PATIENT_IDENTITY_STATUSES.has(identity_status)) {
    res.status(422).json({ detail: 'Invalid patient identity status' })
    return
  }
  for (const existing of store.patients.values()) {
    if (
      existing.hospital_id === ctx.hospitalId &&
      existing.synthetic_mrn === synthetic_mrn
    ) {
      res.status(409).json({ detail: 'Patient could not be created' })
      return
    }
  }
  const patient: Patient = {
    id: crypto.randomUUID(),
    hospital_id: ctx.hospitalId,
    synthetic_mrn,
    given_name,
    family_name,
    date_of_birth,
    sex_at_birth,
    identity_status,
    merged_into_patient_id: null,
  }
  store.patients.set(patient.id, patient)
  res.status(201).json(patient)
})

apiRouter.get(
  '/patients',
  requireRoles('doctor', 'staff', 'pharmacist'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    if (ctx.assignment.relationship_scope !== 'hospital') {
      res
        .status(403)
        .json({ detail: 'Patient search requires hospital relationship scope' })
      return
    }
    const q = typeof req.query.q === 'string' ? req.query.q.trim().toLowerCase() : ''
    const rawLimit = Number.parseInt(String(req.query.limit ?? '25'), 10)
    const limit = Number.isFinite(rawLimit)
      ? Math.min(Math.max(rawLimit, 1), 100)
      : 25

    const results: Patient[] = []
    for (const patient of store.patients.values()) {
      if (
        patient.hospital_id !== ctx.hospitalId ||
        patient.merged_into_patient_id !== null
      ) {
        continue
      }
      if (q) {
        const hay =
          `${patient.synthetic_mrn} ${patient.given_name} ${patient.family_name}`.toLowerCase()
        if (!hay.includes(q)) continue
      }
      results.push(patient)
      if (results.length >= limit) break
    }
    res.json(results)
  },
)

apiRouter.get(
  '/patients/:patientId',
  requireRoles('doctor', 'staff', 'pharmacist'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const patient = getPatientInHospital(ctx, String(req.params.patientId), res)
    if (!patient) return
    res.json(patient)
  },
)

apiRouter.get(
  '/patients/:patientId/timeline',
  requireRoles('doctor', 'staff'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const patient = getPatientInHospital(ctx, String(req.params.patientId), res)
    if (!patient) return

    const toDateOnly = (iso: string | null | undefined) =>
      iso ? iso.slice(0, 10) : null

    const items: Array<{
      item_type: string
      id: string
      status: string
      at: string | null
    }> = []

    for (const row of store.appointments.values()) {
      if (row.hospital_id === ctx.hospitalId && row.patient_id === patient.id) {
        items.push({
          item_type: 'appointment',
          id: row.id,
          status: row.status,
          at: toDateOnly(row.scheduled_at),
        })
      }
    }
    for (const row of store.encounters.values()) {
      if (row.hospital_id === ctx.hospitalId && row.patient_id === patient.id) {
        items.push({
          item_type: 'encounter',
          id: row.id,
          status: row.status,
          at: toDateOnly(row.started_at ?? row.created_at),
        })
      }
    }
    for (const row of store.conditions.values()) {
      if (row.hospital_id === ctx.hospitalId && row.patient_id === patient.id) {
        items.push({
          item_type: 'condition',
          id: row.id,
          status: row.status,
          at: toDateOnly(row.recorded_at),
        })
      }
    }
    for (const row of store.allergies.values()) {
      if (row.hospital_id === ctx.hospitalId && row.patient_id === patient.id) {
        items.push({
          item_type: 'allergy',
          id: row.id,
          status: row.status,
          at: toDateOnly(row.reported_at ?? row.recorded_at),
        })
      }
    }
    for (const row of store.observations.values()) {
      if (row.hospital_id === ctx.hospitalId && row.patient_id === patient.id) {
        items.push({
          item_type: 'observation',
          id: row.id,
          status: 'recorded',
          at: toDateOnly(row.reported_at ?? row.recorded_at),
        })
      }
    }
    for (const row of store.medications.values()) {
      if (row.hospital_id === ctx.hospitalId && row.patient_id === patient.id) {
        items.push({
          item_type: 'medication',
          id: row.id,
          status: row.status,
          at: toDateOnly(row.recorded_at),
        })
      }
    }

    items.sort((a, b) => (b.at ?? '').localeCompare(a.at ?? ''))
    res.json(items)
  },
)

// Appointments
apiRouter.post(
  '/appointments',
  requireRoles('doctor', 'staff'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const { patient_id, doctor_hospital_user_id, scheduled_at } = req.body ?? {}
    const patient = getPatientInHospital(ctx, patient_id, res)
    if (!patient) return
    const doctor = isValidUuid(doctor_hospital_user_id)
      ? store.hospitalUsers.get(doctor_hospital_user_id)
      : undefined
    if (!doctor || doctor.hospital_id !== ctx.hospitalId || doctor.status !== 'active') {
      res
        .status(404)
        .json({ detail: 'Doctor assignment not found in the requested hospital' })
      return
    }
    if (typeof scheduled_at !== 'string' || Number.isNaN(Date.parse(scheduled_at))) {
      res.status(422).json({ detail: 'Valid scheduled_at is required' })
      return
    }
    const appointment = {
      id: crypto.randomUUID(),
      hospital_id: ctx.hospitalId,
      patient_id: patient.id,
      doctor_hospital_user_id: doctor.id,
      scheduled_at,
      status: 'scheduled',
    }
    store.appointments.set(appointment.id, appointment)
    res.status(201).json(appointment)
  },
)

apiRouter.get(
  '/appointments',
  requireRoles('doctor', 'staff'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const patientId =
      typeof req.query.patient_id === 'string' ? req.query.patient_id : null
    const list = []
    for (const appointment of store.appointments.values()) {
      if (appointment.hospital_id !== ctx.hospitalId) continue
      if (patientId && appointment.patient_id !== patientId) continue
      list.push(appointment)
    }
    res.json(list)
  },
)

apiRouter.get(
  '/appointments/:appointmentId',
  requireRoles('doctor', 'staff'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const appointment = store.appointments.get(String(req.params.appointmentId))
    if (!appointment || appointment.hospital_id !== ctx.hospitalId) {
      res.status(404).json({ detail: 'Appointment not found' })
      return
    }
    res.json(appointment)
  },
)

apiRouter.patch(
  '/appointments/:appointmentId/status',
  requireRoles('doctor', 'staff'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const nextStatus = req.body?.status
    if (!APPOINTMENT_STATUSES.has(nextStatus)) {
      res.status(422).json({ detail: 'Invalid appointment status' })
      return
    }
    const appointment = store.appointments.get(String(req.params.appointmentId))
    if (!appointment || appointment.hospital_id !== ctx.hospitalId) {
      res.status(404).json({ detail: 'Appointment not found' })
      return
    }
    appointment.status = nextStatus
    res.json(appointment)
  },
)

// Encounters
apiRouter.post(
  '/encounters',
  requireRoles('doctor', 'staff'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const {
      patient_id,
      appointment_id = null,
      doctor_hospital_user_id,
      started_at = null,
      ended_at = null,
      status = 'planned',
    } = req.body ?? {}

    const patient = getPatientInHospital(ctx, patient_id, res)
    if (!patient) return
    if (!ENCOUNTER_STATUSES.has(status)) {
      res.status(422).json({ detail: 'Invalid encounter status' })
      return
    }
    if (started_at && ended_at && Date.parse(ended_at) < Date.parse(started_at)) {
      res
        .status(422)
        .json({ detail: 'Encounter end time cannot precede start time' })
      return
    }
    const doctor = isValidUuid(doctor_hospital_user_id)
      ? store.hospitalUsers.get(doctor_hospital_user_id)
      : undefined
    if (!doctor || doctor.hospital_id !== ctx.hospitalId || doctor.status !== 'active') {
      res
        .status(404)
        .json({ detail: 'Doctor assignment not found in the requested hospital' })
      return
    }
    if (appointment_id) {
      const appointment = store.appointments.get(appointment_id)
      if (!appointment || appointment.hospital_id !== ctx.hospitalId) {
        res
          .status(404)
          .json({ detail: 'Appointment not found in the requested hospital' })
        return
      }
      if (appointment.patient_id !== patient.id) {
        res
          .status(409)
          .json({ detail: 'Encounter patient does not match appointment patient' })
        return
      }
    }
    const encounter = {
      id: crypto.randomUUID(),
      hospital_id: ctx.hospitalId,
      patient_id: patient.id,
      appointment_id,
      doctor_hospital_user_id: doctor.id,
      started_at,
      ended_at,
      status,
      created_at: new Date().toISOString(),
    }
    store.encounters.set(encounter.id, encounter)
    res.status(201).json(encounter)
  },
)

apiRouter.get(
  '/encounters',
  requireRoles('doctor', 'staff'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const list = []
    for (const encounter of store.encounters.values()) {
      if (encounter.hospital_id === ctx.hospitalId) list.push(encounter)
    }
    res.json(list)
  },
)

apiRouter.get(
  '/encounters/:encounterId',
  requireRoles('doctor', 'staff'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const encounter = store.encounters.get(String(req.params.encounterId))
    if (!encounter || encounter.hospital_id !== ctx.hospitalId) {
      res.status(404).json({ detail: 'Encounter not found' })
      return
    }
    res.json(encounter)
  },
)

apiRouter.patch(
  '/encounters/:encounterId/status',
  requireRoles('doctor'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const { status, started_at, ended_at } = req.body ?? {}
    if (!ENCOUNTER_STATUSES.has(status)) {
      res.status(422).json({ detail: 'Invalid encounter status' })
      return
    }
    const encounter = store.encounters.get(String(req.params.encounterId))
    if (!encounter || encounter.hospital_id !== ctx.hospitalId) {
      res.status(404).json({ detail: 'Encounter not found' })
      return
    }
    const nextStarted = started_at ?? encounter.started_at
    const nextEnded = ended_at ?? encounter.ended_at
    if (
      nextStarted &&
      nextEnded &&
      Date.parse(nextEnded) < Date.parse(nextStarted)
    ) {
      res
        .status(422)
        .json({ detail: 'Encounter end time cannot precede start time' })
      return
    }
    encounter.status = status
    encounter.started_at = nextStarted
    encounter.ended_at = nextEnded
    res.json(encounter)
  },
)

// Provenance & Clinical History
apiRouter.post(
  '/provenance',
  requireRoles('doctor', 'staff'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const body = req.body ?? {}
    if (!SOURCE_TYPES.has(body.source_type)) {
      res.status(422).json({ detail: 'Invalid source type' })
      return
    }
    if (!VERIFICATION_STATUSES.has(body.verification_status)) {
      res.status(422).json({ detail: 'Invalid verification status' })
      return
    }
    if (body.encounter_id && !body.patient_id) {
      res
        .status(409)
        .json({ detail: 'Encounter-linked provenance requires a patient' })
      return
    }
    if (body.patient_id) {
      const patient = getPatientInHospital(ctx, body.patient_id, res)
      if (!patient) return
      if (!validateEncounterForPatient(ctx, body.encounter_id, patient.id, res)) {
        return
      }
    }
    const record = {
      id: crypto.randomUUID(),
      hospital_id: ctx.hospitalId,
      patient_id: body.patient_id ?? null,
      encounter_id: body.encounter_id ?? null,
      source_type: body.source_type,
      source_record_id: body.source_record_id ?? null,
      author_hospital_user_id: body.author_hospital_user_id ?? null,
      recorded_at: body.recorded_at ?? new Date().toISOString(),
      source_at: body.source_at ?? null,
      verification_status: body.verification_status,
      uncertainty: body.uncertainty ?? 'unknown',
      confidence: body.confidence ?? null,
      notes: body.notes ?? null,
    }
    store.provenanceRecords.set(record.id, record)
    res.status(201).json(record)
  },
)

apiRouter.get(
  '/provenance',
  requireRoles('doctor', 'staff'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const patientId =
      typeof req.query.patient_id === 'string' ? req.query.patient_id : null
    if (patientId && !getPatientInHospital(ctx, patientId, res)) return
    const list = []
    for (const row of store.provenanceRecords.values()) {
      if (row.hospital_id !== ctx.hospitalId) continue
      if (patientId && row.patient_id !== patientId) continue
      list.push(row)
    }
    res.json(list)
  },
)

function validateProvenance(
  ctx: AuthorizationContext,
  provenanceId: string,
  patientId: string,
  res: Response,
): boolean {
  if (!isValidUuid(provenanceId)) {
    res.status(422).json({ detail: 'Invalid provenance_id' })
    return false
  }
  const provenance = store.provenanceRecords.get(provenanceId)
  if (!provenance || provenance.hospital_id !== ctx.hospitalId) {
    res
      .status(404)
      .json({ detail: 'Provenance record not found in the requested hospital' })
    return false
  }
  if (!provenance.patient_id) {
    res
      .status(409)
      .json({ detail: 'Typed clinical facts require patient-linked provenance' })
    return false
  }
  if (provenance.patient_id !== patientId) {
    res
      .status(409)
      .json({ detail: 'Provenance record does not belong to the patient' })
    return false
  }
  return true
}

apiRouter.post(
  '/conditions',
  requireRoles('doctor', 'staff'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const body = req.body ?? {}
    const patient = getPatientInHospital(ctx, body.patient_id, res)
    if (!patient) return
    if (!validateEncounterForPatient(ctx, body.encounter_id, patient.id, res)) {
      return
    }
    if (!validateProvenance(ctx, body.provenance_id, patient.id, res)) return
    const row = {
      id: crypto.randomUUID(),
      hospital_id: ctx.hospitalId,
      patient_id: patient.id,
      encounter_id: body.encounter_id ?? null,
      provenance_id: body.provenance_id,
      code_system: body.code_system ?? null,
      code_value: body.code_value ?? null,
      display_name: body.display_name,
      status: body.status,
      verification_status: body.verification_status,
      onset_at: body.onset_at ?? null,
      superseded_by_condition_id: body.superseded_by_condition_id ?? null,
      recorded_at: new Date().toISOString(),
    }
    store.conditions.set(row.id, row)
    res.status(201).json(row)
  },
)

apiRouter.get(
  '/conditions',
  requireRoles('doctor', 'staff'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const patientId =
      typeof req.query.patient_id === 'string' ? req.query.patient_id : null
    if (patientId && !getPatientInHospital(ctx, patientId, res)) return
    const list = []
    for (const row of store.conditions.values()) {
      if (row.hospital_id !== ctx.hospitalId) continue
      if (patientId && row.patient_id !== patientId) continue
      list.push(row)
    }
    res.json(list)
  },
)

apiRouter.post(
  '/allergies',
  requireRoles('doctor', 'staff'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const body = req.body ?? {}
    const patient = getPatientInHospital(ctx, body.patient_id, res)
    if (!patient) return
    if (!validateEncounterForPatient(ctx, body.encounter_id, patient.id, res)) {
      return
    }
    if (!validateProvenance(ctx, body.provenance_id, patient.id, res)) return
    if (body.criticality && !ALLERGY_CRITICALITIES.has(body.criticality)) {
      res.status(422).json({ detail: 'Invalid allergy criticality' })
      return
    }
    const row = {
      id: crypto.randomUUID(),
      hospital_id: ctx.hospitalId,
      patient_id: patient.id,
      encounter_id: body.encounter_id ?? null,
      provenance_id: body.provenance_id,
      substance: body.substance,
      reaction: body.reaction ?? null,
      criticality: body.criticality ?? null,
      status: body.status,
      verification_status: body.verification_status,
      reported_at: body.reported_at ?? null,
      recorded_at: new Date().toISOString(),
    }
    store.allergies.set(row.id, row)
    res.status(201).json(row)
  },
)

apiRouter.get(
  '/allergies',
  requireRoles('doctor', 'staff'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const patientId =
      typeof req.query.patient_id === 'string' ? req.query.patient_id : null
    if (patientId && !getPatientInHospital(ctx, patientId, res)) return
    const list = []
    for (const row of store.allergies.values()) {
      if (row.hospital_id !== ctx.hospitalId) continue
      if (patientId && row.patient_id !== patientId) continue
      list.push(row)
    }
    res.json(list)
  },
)

apiRouter.post(
  '/observations',
  requireRoles('doctor', 'staff'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const body = req.body ?? {}
    const patient = getPatientInHospital(ctx, body.patient_id, res)
    if (!patient) return
    if (!validateEncounterForPatient(ctx, body.encounter_id, patient.id, res)) {
      return
    }
    if (!validateProvenance(ctx, body.provenance_id, patient.id, res)) return
    if (body.value_text == null && body.value_numeric == null) {
      res
        .status(422)
        .json({ detail: 'Observation requires text or numeric value' })
      return
    }
    const row = {
      id: crypto.randomUUID(),
      hospital_id: ctx.hospitalId,
      patient_id: patient.id,
      encounter_id: body.encounter_id ?? null,
      provenance_id: body.provenance_id,
      observation_type: body.observation_type,
      test_name: body.test_name ?? null,
      value_text: body.value_text ?? null,
      value_numeric: body.value_numeric ?? null,
      unit: body.unit ?? null,
      reference_range: body.reference_range ?? null,
      reported_at: body.reported_at ?? null,
      recorded_at: new Date().toISOString(),
    }
    store.observations.set(row.id, row)
    res.status(201).json(row)
  },
)

apiRouter.get(
  '/observations',
  requireRoles('doctor', 'staff'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const patientId =
      typeof req.query.patient_id === 'string' ? req.query.patient_id : null
    if (patientId && !getPatientInHospital(ctx, patientId, res)) return
    const list = []
    for (const row of store.observations.values()) {
      if (row.hospital_id !== ctx.hospitalId) continue
      if (patientId && row.patient_id !== patientId) continue
      list.push(row)
    }
    res.json(list)
  },
)

apiRouter.post(
  '/medications',
  requireRoles('doctor', 'staff'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const body = req.body ?? {}
    const patient = getPatientInHospital(ctx, body.patient_id, res)
    if (!patient) return
    if (!validateEncounterForPatient(ctx, body.encounter_id, patient.id, res)) {
      return
    }
    if (!validateProvenance(ctx, body.provenance_id, patient.id, res)) return
    if (
      body.start_at &&
      body.end_at &&
      Date.parse(body.end_at) < Date.parse(body.start_at)
    ) {
      res.status(422).json({ detail: 'Medication end cannot precede start' })
      return
    }
    const row = {
      id: crypto.randomUUID(),
      hospital_id: ctx.hospitalId,
      patient_id: patient.id,
      encounter_id: body.encounter_id ?? null,
      provenance_id: body.provenance_id,
      medicine_name: body.medicine_name,
      catalogue_item_id: body.catalogue_item_id ?? null,
      statement_type: body.statement_type,
      status: body.status,
      dose: body.dose ?? null,
      start_at: body.start_at ?? null,
      end_at: body.end_at ?? null,
      superseded_by_statement_id: body.superseded_by_statement_id ?? null,
      verification_status: body.verification_status,
      recorded_at: new Date().toISOString(),
    }
    store.medications.set(row.id, row)
    res.status(201).json(row)
  },
)

apiRouter.get(
  '/medications',
  requireRoles('doctor', 'staff'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const patientId =
      typeof req.query.patient_id === 'string' ? req.query.patient_id : null
    if (patientId && !getPatientInHospital(ctx, patientId, res)) return
    const list = []
    for (const row of store.medications.values()) {
      if (row.hospital_id !== ctx.hospitalId) continue
      if (patientId && row.patient_id !== patientId) continue
      list.push(row)
    }
    res.json(list)
  },
)

// Clinical Notes Drafts
apiRouter.post(
  '/clinical-notes/drafts',
  requireRoles('doctor'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const body = req.body ?? {}
    const patient = getPatientInHospital(ctx, body.patient_id, res)
    if (!patient) return
    if (!body.encounter_id) {
      res.status(422).json({ detail: 'encounter_id is required' })
      return
    }
    if (!validateEncounterForPatient(ctx, body.encounter_id, patient.id, res)) {
      return
    }
    if (
      typeof body.transcript_text !== 'string' ||
      !body.transcript_text.trim() ||
      typeof body.chief_complaint !== 'string' ||
      !body.chief_complaint.trim()
    ) {
      res
        .status(422)
        .json({ detail: 'transcript_text and chief_complaint are required' })
      return
    }
    const nowIso = new Date().toISOString()
    const draft: ClinicalNoteDraft = {
      id: crypto.randomUUID(),
      hospital_id: ctx.hospitalId,
      patient_id: patient.id,
      encounter_id: body.encounter_id,
      created_by_hospital_user_id: ctx.assignment.id,
      transcript_text: body.transcript_text,
      chief_complaint: body.chief_complaint,
      history: body.history ?? '',
      patient_facts: body.patient_facts ?? '',
      doctor_questions: body.doctor_questions ?? '',
      examination_findings: body.examination_findings ?? '',
      assessment: body.assessment ?? '',
      plan: body.plan ?? '',
      missing_information: body.missing_information ?? '',
      status: 'draft',
      created_at: nowIso,
      updated_at: nowIso,
    }
    store.clinicalNoteDrafts.set(draft.id, draft)
    res.status(201).json(draft)
  },
)

apiRouter.get(
  '/clinical-notes/drafts',
  requireRoles('doctor'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const patientId =
      typeof req.query.patient_id === 'string' ? req.query.patient_id : ''
    if (!getPatientInHospital(ctx, patientId, res)) return
    const list: ClinicalNoteDraft[] = []
    for (const draft of store.clinicalNoteDrafts.values()) {
      if (
        draft.hospital_id === ctx.hospitalId &&
        draft.patient_id === patientId
      ) {
        list.push(draft)
      }
    }
    list.sort((a, b) => b.created_at.localeCompare(a.created_at))
    res.json(list)
  },
)

apiRouter.patch(
  '/clinical-notes/drafts/:draftId/approval',
  requireRoles('doctor'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const draft = store.clinicalNoteDrafts.get(String(req.params.draftId))
    if (!draft || draft.hospital_id !== ctx.hospitalId) {
      res.status(404).json({ detail: 'Clinical note draft not found' })
      return
    }
    if (!validatePatientObjectAccess(ctx.assignment, draft.patient_id)) {
      res
        .status(403)
        .json({ detail: 'No approved patient relationship for this operation' })
      return
    }
    if (draft.status !== 'draft') {
      res
        .status(409)
        .json({ detail: 'Only an existing draft can be approved or cancelled' })
      return
    }
    draft.status = req.body?.approved ? 'approved' : 'cancelled'
    draft.updated_at = new Date().toISOString()
    res.json(draft)
  },
)

// Medicine Catalogue & Prescriptions
apiRouter.post(
  '/catalogue/items',
  requireRoles('doctor', 'staff'),
  (req: AuthenticatedRequest, res) => {
    const body = req.body ?? {}
    if (
      !body.catalogue_name ||
      !body.catalogue_version ||
      !body.generic_name ||
      !body.source_name
    ) {
      res.status(422).json({ detail: 'Missing required catalogue fields' })
      return
    }
    const item = {
      id: crypto.randomUUID(),
      catalogue_name: body.catalogue_name,
      catalogue_version: body.catalogue_version,
      generic_name: body.generic_name,
      brand_name: body.brand_name ?? null,
      active_ingredient: body.active_ingredient ?? null,
      manufacturer: body.manufacturer ?? null,
      strength: body.strength ?? null,
      dosage_form: body.dosage_form ?? null,
      route: body.route ?? null,
      prescribing_information: body.prescribing_information ?? null,
      source_name: body.source_name,
      source_uri: body.source_uri ?? null,
      source_updated_at: body.source_updated_at ?? null,
      status: 'active',
    }
    store.catalogueItems.set(item.id, item)
    res.status(201).json(item)
  },
)

apiRouter.get(
  '/catalogue/items',
  requireRoles('doctor', 'staff', 'pharmacist'),
  (req: AuthenticatedRequest, res) => {
    const q = typeof req.query.q === 'string' ? req.query.q.trim().toLowerCase() : ''
    const results = []
    for (const item of store.catalogueItems.values()) {
      if (item.status !== 'active') continue
      if (q) {
        const hay = `${item.generic_name} ${item.brand_name ?? ''}`.toLowerCase()
        if (!hay.includes(q)) continue
      }
      results.push(item)
      if (results.length >= 100) break
    }
    res.json(results)
  },
)

apiRouter.post(
  '/prescription-drafts',
  requireRoles('doctor'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const body = req.body ?? {}
    const patient = getPatientInHospital(ctx, body.patient_id, res)
    if (!patient) return
    if (!body.encounter_id) {
      res.status(422).json({ detail: 'encounter_id is required' })
      return
    }
    if (!validateEncounterForPatient(ctx, body.encounter_id, patient.id, res)) {
      return
    }
    if (!Array.isArray(body.lines) || body.lines.length === 0) {
      res.status(422).json({ detail: 'At least one prescription line is required' })
      return
    }
    for (const line of body.lines) {
      if (line.catalogue_item_id) {
        const item = store.catalogueItems.get(line.catalogue_item_id)
        if (!item || item.status !== 'active') {
          res.status(404).json({ detail: 'Active catalogue item not found' })
          return
        }
      }
    }

    const draft: PrescriptionDraft = {
      id: crypto.randomUUID(),
      hospital_id: ctx.hospitalId,
      patient_id: patient.id,
      encounter_id: body.encounter_id,
      created_by_hospital_user_id: ctx.assignment.id,
      status: 'draft',
      created_at: new Date().toISOString(),
    }
    store.prescriptionDrafts.set(draft.id, draft)

    const savedLines: PrescriptionDraftLine[] = []
    for (const line of body.lines) {
      const saved: PrescriptionDraftLine = {
        id: crypto.randomUUID(),
        hospital_id: ctx.hospitalId,
        draft_id: draft.id,
        catalogue_item_id: line.catalogue_item_id ?? null,
        medicine_name: line.medicine_name,
        strength: line.strength ?? null,
        dose: line.dose ?? null,
        route: line.route ?? null,
        frequency: line.frequency ?? null,
        duration: line.duration ?? null,
        quantity: line.quantity ?? null,
        instructions: line.instructions ?? null,
      }
      store.prescriptionDraftLines.set(saved.id, saved)
      savedLines.push(saved)
    }

    const warnings = getSafetyWarnings(ctx.hospitalId, patient.id, savedLines)
    res.status(201).json(buildDraftResponse(draft, savedLines, warnings))
  },
)

apiRouter.get(
  '/prescription-drafts/:draftId',
  requireRoles('doctor', 'staff'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const draft = store.prescriptionDrafts.get(String(req.params.draftId))
    if (!draft || draft.hospital_id !== ctx.hospitalId) {
      res.status(404).json({ detail: 'Prescription draft not found' })
      return
    }
    if (!validatePatientObjectAccess(ctx.assignment, draft.patient_id)) {
      res
        .status(403)
        .json({ detail: 'No approved patient relationship for this operation' })
      return
    }
    const lines = Array.from(store.prescriptionDraftLines.values()).filter(
      (line) =>
        line.hospital_id === ctx.hospitalId && line.draft_id === draft.id,
    )
    const warnings = getSafetyWarnings(ctx.hospitalId, draft.patient_id, lines)
    res.json(buildDraftResponse(draft, lines, warnings))
  },
)

apiRouter.patch(
  '/prescription-drafts/:draftId/approval',
  requireRoles('doctor'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const draft = store.prescriptionDrafts.get(String(req.params.draftId))
    if (!draft || draft.hospital_id !== ctx.hospitalId) {
      res.status(404).json({ detail: 'Prescription draft not found' })
      return
    }
    if (!validatePatientObjectAccess(ctx.assignment, draft.patient_id)) {
      res
        .status(403)
        .json({ detail: 'No approved patient relationship for this operation' })
      return
    }
    if (draft.status !== 'draft') {
      res
        .status(409)
        .json({ detail: 'Only an existing draft may be approved or rejected' })
      return
    }
    draft.status = req.body?.approved ? 'approved' : 'cancelled'
    const lines = Array.from(store.prescriptionDraftLines.values()).filter(
      (line) =>
        line.hospital_id === ctx.hospitalId && line.draft_id === draft.id,
    )
    res.json(buildDraftResponse(draft, lines, []))
  },
)

apiRouter.post(
  '/prescriptions',
  requireRoles('doctor'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const draftId =
      typeof req.query.draft_id === 'string' ? req.query.draft_id : ''
    const draft = store.prescriptionDrafts.get(draftId)
    if (!draft || draft.hospital_id !== ctx.hospitalId) {
      res.status(404).json({ detail: 'Prescription draft not found' })
      return
    }
    if (!validatePatientObjectAccess(ctx.assignment, draft.patient_id)) {
      res
        .status(403)
        .json({ detail: 'No approved patient relationship for this operation' })
      return
    }
    if (draft.status !== 'approved') {
      res.status(409).json({ detail: 'Only an approved draft may be signed' })
      return
    }
    const draftLines = Array.from(store.prescriptionDraftLines.values()).filter(
      (line) =>
        line.hospital_id === ctx.hospitalId && line.draft_id === draft.id,
    )
    const prescription: SignedPrescription = {
      id: crypto.randomUUID(),
      hospital_id: ctx.hospitalId,
      patient_id: draft.patient_id,
      encounter_id: draft.encounter_id,
      draft_id: draft.id,
      prescribing_hospital_user_id: ctx.assignment.id,
      signed_at: new Date().toISOString(),
      status: 'signed',
      signature_reference: req.body?.signature_reference ?? null,
    }
    store.signedPrescriptions.set(prescription.id, prescription)

    const signedLines: PrescriptionLine[] = []
    for (const line of draftLines) {
      const signedLine: PrescriptionLine = {
        id: crypto.randomUUID(),
        hospital_id: ctx.hospitalId,
        prescription_id: prescription.id,
        catalogue_item_id: line.catalogue_item_id,
        medicine_name: line.medicine_name,
        strength: line.strength,
        dose: line.dose,
        route: line.route,
        frequency: line.frequency,
        duration: line.duration,
        quantity: line.quantity,
        instructions: line.instructions,
      }
      store.prescriptionLines.set(signedLine.id, signedLine)
      signedLines.push(signedLine)
    }

    res.status(201).json(buildPrescriptionResponse(prescription, signedLines))
  },
)

apiRouter.get(
  '/pharmacy/prescriptions/:prescriptionId',
  requireRoles('pharmacist'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const prescription = store.signedPrescriptions.get(
      String(req.params.prescriptionId),
    )
    if (!prescription || prescription.hospital_id !== ctx.hospitalId) {
      res.status(404).json({ detail: 'Prescription not found' })
      return
    }
    if (!validatePatientObjectAccess(ctx.assignment, prescription.patient_id)) {
      res
        .status(403)
        .json({ detail: 'No approved patient relationship for this operation' })
      return
    }
    const lines = Array.from(store.prescriptionLines.values()).filter(
      (line) =>
        line.hospital_id === ctx.hospitalId &&
        line.prescription_id === prescription.id,
    )
    res.json({
      prescription_id: prescription.id,
      patient_id: prescription.patient_id,
      prescriber_hospital_user_id: prescription.prescribing_hospital_user_id,
      signed_at: prescription.signed_at,
      status: prescription.status,
      lines,
    })
  },
)

apiRouter.post(
  '/dispensing',
  requireRoles('pharmacist'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const prescription = store.signedPrescriptions.get(
      String(req.body?.prescription_id ?? ''),
    )
    if (!prescription || prescription.hospital_id !== ctx.hospitalId) {
      res.status(404).json({ detail: 'Prescription not found' })
      return
    }
    if (!validatePatientObjectAccess(ctx.assignment, prescription.patient_id)) {
      res
        .status(403)
        .json({ detail: 'No approved patient relationship for this operation' })
      return
    }
    const record = {
      id: crypto.randomUUID(),
      hospital_id: ctx.hospitalId,
      patient_id: prescription.patient_id,
      prescription_id: prescription.id,
      pharmacist_hospital_user_id: ctx.assignment.id,
      status: 'viewed',
      substitution_allowed: false,
      substitution_text: null,
      clarification_text: null,
      dispensed_at: null,
    }
    store.dispensingRecords.set(record.id, record)
    res.status(201).json(record)
  },
)

// Documents & Source References
apiRouter.post(
  '/documents',
  requireRoles('doctor', 'staff'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const body = req.body ?? {}
    if (!ALLOWED_MIME_TYPES.has(body.mime_type)) {
      res.status(422).json({ detail: 'Unsupported document MIME type' })
      return
    }
    if (body.sha256 != null && !/^[0-9a-f]{64}$/i.test(String(body.sha256))) {
      res
        .status(422)
        .json({ detail: 'SHA-256 must contain 64 hexadecimal characters' })
      return
    }
    const patient = getPatientInHospital(ctx, body.patient_id, res)
    if (!patient) return
    if (!validateEncounterForPatient(ctx, body.encounter_id, patient.id, res)) {
      return
    }
    const doc: MedicalDocument = {
      id: crypto.randomUUID(),
      hospital_id: ctx.hospitalId,
      patient_id: patient.id,
      encounter_id: body.encounter_id ?? null,
      document_type: body.document_type,
      original_name: body.original_name,
      mime_type: body.mime_type,
      object_uri: body.object_uri,
      sha256: body.sha256 ? String(body.sha256).toLowerCase() : null,
      document_date: body.document_date ?? null,
      upload_date: new Date().toISOString(),
      issuing_source: body.issuing_source ?? null,
      page_count: body.page_count ?? null,
      processing_status: body.processing_status ?? 'uploaded',
      retention_status: body.retention_status ?? 'active',
      uploaded_by_hospital_user_id: ctx.assignment.id,
    }
    store.documents.set(doc.id, doc)
    res.status(201).json(doc)
  },
)

apiRouter.get(
  '/documents',
  requireRoles('doctor', 'staff'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const list = []
    for (const doc of store.documents.values()) {
      if (
        doc.hospital_id === ctx.hospitalId &&
        validatePatientObjectAccess(ctx.assignment, doc.patient_id)
      ) {
        list.push(doc)
      }
    }
    res.json(list)
  },
)

apiRouter.get(
  '/documents/:documentId',
  requireRoles('doctor', 'staff'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const doc = getDocumentInHospital(ctx, String(req.params.documentId), res)
    if (!doc) return
    res.json(doc)
  },
)

apiRouter.post(
  '/documents/:documentId/pages',
  requireRoles('doctor', 'staff'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const doc = getDocumentInHospital(ctx, String(req.params.documentId), res)
    if (!doc) return
    const page = {
      id: crypto.randomUUID(),
      hospital_id: ctx.hospitalId,
      document_id: doc.id,
      page_number: Number(req.body?.page_number ?? 1),
      width: req.body?.width ?? null,
      height: req.body?.height ?? null,
      text_source: req.body?.text_source ?? null,
    }
    store.documentPages.set(page.id, page)
    res.status(201).json(page)
  },
)

apiRouter.get(
  '/documents/:documentId/pages',
  requireRoles('doctor', 'staff'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const doc = getDocumentInHospital(ctx, String(req.params.documentId), res)
    if (!doc) return
    const pages = Array.from(store.documentPages.values())
      .filter(
        (page) =>
          page.hospital_id === ctx.hospitalId && page.document_id === doc.id,
      )
      .sort((a, b) => a.page_number - b.page_number)
    res.json(pages)
  },
)

apiRouter.post(
  '/documents/:documentId/pages/:pageId/regions',
  requireRoles('doctor', 'staff'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const doc = getDocumentInHospital(ctx, String(req.params.documentId), res)
    if (!doc) return
    const page = store.documentPages.get(String(req.params.pageId))
    if (!page || page.hospital_id !== ctx.hospitalId || page.document_id !== doc.id) {
      res.status(404).json({ detail: 'Document page not found' })
      return
    }
    const region = {
      id: crypto.randomUUID(),
      hospital_id: ctx.hospitalId,
      document_page_id: page.id,
      region_type: req.body?.region_type ?? 'text',
      x: req.body?.x ?? null,
      y: req.body?.y ?? null,
      width: req.body?.width ?? null,
      height: req.body?.height ?? null,
      text: req.body?.text ?? null,
      confidence: req.body?.confidence ?? null,
    }
    store.documentRegions.set(region.id, region)
    res.status(201).json(region)
  },
)

apiRouter.post(
  '/documents/:documentId/extractions',
  requireRoles('doctor', 'staff'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const doc = getDocumentInHospital(ctx, String(req.params.documentId), res)
    if (!doc) return
    if (req.body?.document_region_id) {
      const region = store.documentRegions.get(req.body.document_region_id)
      if (!region || region.hospital_id !== ctx.hospitalId) {
        res.status(404).json({ detail: 'Document region not found' })
        return
      }
      const page = store.documentPages.get(region.document_page_id)
      if (!page || page.document_id !== doc.id) {
        res
          .status(409)
          .json({ detail: 'Extraction region does not belong to the document' })
        return
      }
    }
    const extraction = {
      id: crypto.randomUUID(),
      hospital_id: ctx.hospitalId,
      document_id: doc.id,
      document_region_id: req.body?.document_region_id ?? null,
      field_name: req.body?.field_name ?? '',
      extracted_value: req.body?.extracted_value ?? null,
      normalized_value: req.body?.normalized_value ?? null,
      unit: req.body?.unit ?? null,
      reference_range: req.body?.reference_range ?? null,
      extraction_status: req.body?.extraction_status ?? 'unverified',
      confidence: req.body?.confidence ?? null,
      reviewed_by_hospital_user_id: null,
      reviewed_at: null,
    }
    store.documentExtractions.set(extraction.id, extraction)
    res.status(201).json(extraction)
  },
)

apiRouter.get(
  '/documents/:documentId/extractions',
  requireRoles('doctor', 'staff'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const doc = getDocumentInHospital(ctx, String(req.params.documentId), res)
    if (!doc) return
    const rows = Array.from(store.documentExtractions.values()).filter(
      (row) => row.hospital_id === ctx.hospitalId && row.document_id === doc.id,
    )
    res.json(rows)
  },
)

apiRouter.post(
  '/documents/:documentId/extractions/:extractionId/corrections',
  requireRoles('doctor'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const doc = getDocumentInHospital(ctx, String(req.params.documentId), res)
    if (!doc) return
    const extraction = store.documentExtractions.get(
      String(req.params.extractionId),
    )
    if (
      !extraction ||
      extraction.hospital_id !== ctx.hospitalId ||
      extraction.document_id !== doc.id
    ) {
      res.status(404).json({ detail: 'Extraction not found' })
      return
    }
    const correction = {
      id: crypto.randomUUID(),
      hospital_id: ctx.hospitalId,
      extraction_id: extraction.id,
      corrected_by_hospital_user_id: ctx.assignment.id,
      previous_value: req.body?.previous_value ?? null,
      corrected_value: req.body?.corrected_value ?? '',
      reason: req.body?.reason ?? '',
      corrected_at: new Date().toISOString(),
    }
    store.documentCorrections.set(correction.id, correction)
    res.status(201).json(correction)
  },
)

// AI Clinical Draft (Server-side Gemini via @google/genai)
apiRouter.post(
  '/ai/clinical-draft',
  requireRoles('doctor'),
  async (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const {
      patient_id,
      encounter_id = null,
      transcript,
      manual_text = '',
    } = req.body ?? {}

    const patient = getPatientInHospital(ctx, patient_id, res)
    if (!patient) return

    if (encounter_id != null) {
      if (!validateEncounterForPatient(ctx, encounter_id, patient.id, res)) {
        return
      }
    }

    if (
      typeof transcript !== 'string' ||
      transcript.trim().length < 1 ||
      transcript.length > 30000
    ) {
      res
        .status(422)
        .json({ detail: 'Transcript must be between 1 and 30000 characters' })
      return
    }

    if (!process.env.GEMINI_API_KEY) {
      res.status(503).json({ detail: 'GEMINI_API_KEY is not configured' })
      return
    }

    try {
      const draft = await generateClinicalDraftWithGemini({
        patient,
        transcript,
        manualText: typeof manual_text === 'string' ? manual_text : '',
      })
      res.json({
        is_ai_draft: true,
        clinical_approval_required: true,
        draft,
        transcript_length: transcript.length,
      })
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Unknown Gemini error'
      if (message === 'GEMINI_API_KEY_MISSING') {
        res.status(503).json({ detail: 'GEMINI_API_KEY is not configured' })
        return
      }
      console.error('[MediFlow AI] Gemini clinical-draft error:', message)
      const safeDetail = message.replace(/AIza[0-9A-Za-z_-]{10,}/g, '[redacted]')
      res.status(502).json({
        detail: `Gemini could not generate a valid clinical draft: ${safeDetail}`,
      })
    }
  },
)

// Personal Patient Notes (Persistence + Approval + Adaptive Gemini Point-Wise Formatting)
apiRouter.post(
  '/personal-notes',
  requireRoles('doctor'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const body = req.body ?? {}
    const patient = getPatientInHospital(ctx, body.patient_id, res)
    if (!patient) return
    if (body.encounter_id != null) {
      if (!validateEncounterForPatient(ctx, body.encounter_id, patient.id, res)) {
        return
      }
    }
    const bulletPoints = Array.isArray(body.bullet_points)
      ? body.bullet_points
          .map((item: unknown) => (typeof item === 'string' ? item.trim() : ''))
          .filter(Boolean)
      : []

    if (bulletPoints.length === 0) {
      res
        .status(422)
        .json({ detail: 'At least one personal note point is required' })
      return
    }

    const inputMode = body.input_mode === 'voice' ? 'voice' : 'written'
    const formatMode =
      body.format_mode === 'concise_polish' ||
      body.format_mode === 'key_points_summary'
        ? body.format_mode
        : 'manual'
    const nowIso = new Date().toISOString()

    const draft: PersonalNoteDraft = {
      id: crypto.randomUUID(),
      hospital_id: ctx.hospitalId,
      patient_id: patient.id,
      encounter_id: body.encounter_id ?? null,
      created_by_hospital_user_id: ctx.assignment.id,
      raw_input_text:
        typeof body.raw_input_text === 'string' ? body.raw_input_text : '',
      input_mode: inputMode,
      format_mode: formatMode,
      title:
        typeof body.title === 'string' && body.title.trim()
          ? body.title.trim()
          : 'Patient Care Instructions',
      bullet_points: bulletPoints,
      status: 'draft',
      created_at: nowIso,
      updated_at: nowIso,
    }
    store.personalNoteDrafts.set(draft.id, draft)
    res.status(201).json(draft)
  },
)

apiRouter.get(
  '/personal-notes',
  requireRoles('doctor'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const patientId =
      typeof req.query.patient_id === 'string' ? req.query.patient_id : ''
    if (!getPatientInHospital(ctx, patientId, res)) return
    const list: PersonalNoteDraft[] = []
    for (const draft of store.personalNoteDrafts.values()) {
      if (
        draft.hospital_id === ctx.hospitalId &&
        draft.patient_id === patientId
      ) {
        list.push(draft)
      }
    }
    list.sort((a, b) => b.created_at.localeCompare(a.created_at))
    res.json(list)
  },
)

apiRouter.patch(
  '/personal-notes/:noteId/approval',
  requireRoles('doctor'),
  (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const draft = store.personalNoteDrafts.get(String(req.params.noteId))
    if (!draft || draft.hospital_id !== ctx.hospitalId) {
      res.status(404).json({ detail: 'Personal note draft not found' })
      return
    }
    if (!validatePatientObjectAccess(ctx.assignment, draft.patient_id)) {
      res
        .status(403)
        .json({ detail: 'No approved patient relationship for this operation' })
      return
    }
    if (draft.status !== 'draft') {
      res
        .status(409)
        .json({ detail: 'Only an existing draft can be approved or cancelled' })
      return
    }
    draft.status = req.body?.approved ? 'approved' : 'cancelled'
    draft.updated_at = new Date().toISOString()
    res.json(draft)
  },
)

apiRouter.post(
  '/ai/personal-notes',
  requireRoles('doctor'),
  async (req: AuthenticatedRequest, res) => {
    const ctx = req.authContext!
    const {
      patient_id,
      encounter_id = null,
      raw_text,
      input_mode = 'written',
    } = req.body ?? {}

    const patient = getPatientInHospital(ctx, patient_id, res)
    if (!patient) return

    if (encounter_id != null) {
      if (!validateEncounterForPatient(ctx, encounter_id, patient.id, res)) {
        return
      }
    }

    if (
      typeof raw_text !== 'string' ||
      raw_text.trim().length < 1 ||
      raw_text.length > 30000
    ) {
      res
        .status(422)
        .json({ detail: 'Note text must be between 1 and 30000 characters' })
      return
    }

    if (!process.env.GEMINI_API_KEY) {
      res.status(503).json({ detail: 'GEMINI_API_KEY is not configured' })
      return
    }

    try {
      const notes = await formatPersonalNotesWithGemini({
        patient,
        rawText: raw_text,
        inputMode: input_mode === 'voice' ? 'voice' : 'written',
      })
      res.json({
        is_ai_draft: true,
        clinical_approval_required: true,
        notes,
      })
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Unknown Gemini error'
      if (message === 'GEMINI_API_KEY_MISSING') {
        res.status(503).json({ detail: 'GEMINI_API_KEY is not configured' })
        return
      }
      console.error('[MediFlow AI] Gemini personal-notes error:', message)
      const safeDetail = message.replace(/AIza[0-9A-Za-z_-]{10,}/g, '[redacted]')
      res.status(502).json({
        detail: `Gemini could not format the personal notes draft: ${safeDetail}`,
      })
    }
  },
)

