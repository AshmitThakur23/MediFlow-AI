import crypto from 'node:crypto'
import type {
  AllergyIntolerance,
  Appointment,
  ClinicalNoteDraft,
  Condition,
  DispensingRecord,
  DocumentExtraction,
  DocumentExtractionCorrection,
  DocumentPage,
  DocumentRegion,
  Encounter,
  Hospital,
  HospitalUser,
  MedicalDocument,
  MedicationStatement,
  MedicineCatalogueItem,
  Observation,
  Patient,
  PrescriptionDraft,
  PrescriptionDraftLine,
  PrescriptionLine,
  ProvenanceRecord,
  SignedPrescription,
  User,
} from './types.ts'

export const DEMO_EMAIL = 'doctor.synthetic@mediflow.local'
export const DEMO_PASSWORD = 'MediFlowDemo123!'

// In-memory synthetic MVP data store (reset on container restart).
export const store = {
  hospitals: new Map<string, Hospital>(),
  users: new Map<string, User>(),
  hospitalUsers: new Map<string, HospitalUser>(),
  patients: new Map<string, Patient>(),
  appointments: new Map<string, Appointment>(),
  encounters: new Map<string, Encounter>(),
  provenanceRecords: new Map<string, ProvenanceRecord>(),
  conditions: new Map<string, Condition>(),
  allergies: new Map<string, AllergyIntolerance>(),
  observations: new Map<string, Observation>(),
  medications: new Map<string, MedicationStatement>(),
  catalogueItems: new Map<string, MedicineCatalogueItem>(),
  prescriptionDrafts: new Map<string, PrescriptionDraft>(),
  prescriptionDraftLines: new Map<string, PrescriptionDraftLine>(),
  signedPrescriptions: new Map<string, SignedPrescription>(),
  prescriptionLines: new Map<string, PrescriptionLine>(),
  dispensingRecords: new Map<string, DispensingRecord>(),
  clinicalNoteDrafts: new Map<string, ClinicalNoteDraft>(),
  documents: new Map<string, MedicalDocument>(),
  documentPages: new Map<string, DocumentPage>(),
  documentRegions: new Map<string, DocumentRegion>(),
  documentExtractions: new Map<string, DocumentExtraction>(),
  documentCorrections: new Map<string, DocumentExtractionCorrection>(),
}

function hashDemoPassword(password: string): string {
  const salt = crypto.randomBytes(16)
  const digest = crypto.pbkdf2Sync(password, salt, 600_000, 32, 'sha256')
  return `pbkdf2_sha256$600000$${salt.toString('base64')}$${digest.toString('base64')}`
}

let seeded = false

export function seedDemoData(): void {
  if (seeded) return
  seeded = true

  const now = Date.now()
  const nowIso = new Date(now).toISOString()

  const hospitalId = crypto.randomUUID()
  store.hospitals.set(hospitalId, {
    id: hospitalId,
    name: 'MediFlow Synthetic Hospital',
    code: 'SYN-001',
    status: 'active',
  })

  const userId = crypto.randomUUID()
  store.users.set(userId, {
    id: userId,
    email: DEMO_EMAIL,
    display_name: 'Dr. Aanya Sharma',
    status: 'active',
    password_hash: hashDemoPassword(DEMO_PASSWORD),
  })

  const doctorId = crypto.randomUUID()
  store.hospitalUsers.set(doctorId, {
    id: doctorId,
    hospital_id: hospitalId,
    user_id: userId,
    role_code: 'doctor',
    relationship_scope: 'hospital',
    status: 'active',
    valid_from: new Date(now - 30 * 24 * 60 * 60 * 1000).toISOString(),
    valid_until: null,
  })

  const syntheticPatients = [
    {
      mrn: 'MRN-DEMO-001',
      given: 'Meera',
      family: 'Patel',
      dob: '1994-05-18',
      sex: 'female',
    },
    {
      mrn: 'MRN-DEMO-002',
      given: 'Rohan',
      family: 'Verma',
      dob: '1981-09-03',
      sex: 'male',
    },
    {
      mrn: 'MRN-DEMO-003',
      given: 'Sara',
      family: 'Khan',
      dob: '1998-01-26',
      sex: 'female',
    },
  ]

  syntheticPatients.forEach((entry, offset) => {
    const patientId = crypto.randomUUID()
    store.patients.set(patientId, {
      id: patientId,
      hospital_id: hospitalId,
      synthetic_mrn: entry.mrn,
      given_name: entry.given,
      family_name: entry.family,
      date_of_birth: entry.dob,
      sex_at_birth: entry.sex,
      identity_status: 'verified',
      merged_into_patient_id: null,
    })

    const appointmentId = crypto.randomUUID()
    store.appointments.set(appointmentId, {
      id: appointmentId,
      hospital_id: hospitalId,
      patient_id: patientId,
      doctor_hospital_user_id: doctorId,
      scheduled_at: new Date(now + 8 * (offset + 1) * 60 * 1000).toISOString(),
      status: 'scheduled',
    })

    const encounterId = crypto.randomUUID()
    store.encounters.set(encounterId, {
      id: encounterId,
      hospital_id: hospitalId,
      patient_id: patientId,
      appointment_id: appointmentId,
      doctor_hospital_user_id: doctorId,
      started_at: null,
      ended_at: null,
      status: 'planned',
      created_at: nowIso,
    })

    if (entry.mrn === 'MRN-DEMO-001') {
      const provenanceId = crypto.randomUUID()
      store.provenanceRecords.set(provenanceId, {
        id: provenanceId,
        hospital_id: hospitalId,
        patient_id: patientId,
        encounter_id: encounterId,
        source_type: 'doctor_entry',
        source_record_id: null,
        author_hospital_user_id: doctorId,
        recorded_at: nowIso,
        source_at: null,
        verification_status: 'reviewed',
        uncertainty: 'unknown',
        confidence: null,
        notes: null,
      })

      const conditionId = crypto.randomUUID()
      store.conditions.set(conditionId, {
        id: conditionId,
        hospital_id: hospitalId,
        patient_id: patientId,
        encounter_id: encounterId,
        provenance_id: provenanceId,
        code_system: null,
        code_value: null,
        display_name: 'Asthma',
        status: 'active',
        verification_status: 'verified',
        onset_at: '2023-04-10T00:00:00.000Z',
        superseded_by_condition_id: null,
        recorded_at: nowIso,
      })

      const allergyId = crypto.randomUUID()
      store.allergies.set(allergyId, {
        id: allergyId,
        hospital_id: hospitalId,
        patient_id: patientId,
        encounter_id: encounterId,
        provenance_id: provenanceId,
        substance: 'Penicillin',
        reaction: 'Rash',
        criticality: 'high',
        status: 'active',
        verification_status: 'verified',
        reported_at: '2024-02-12T00:00:00.000Z',
        recorded_at: nowIso,
      })

      const observationId = crypto.randomUUID()
      store.observations.set(observationId, {
        id: observationId,
        hospital_id: hospitalId,
        patient_id: patientId,
        encounter_id: encounterId,
        provenance_id: provenanceId,
        observation_type: 'vital',
        test_name: 'Oxygen saturation',
        value_text: '98%',
        value_numeric: null,
        unit: '%',
        reference_range: null,
        reported_at: '2026-11-18T00:00:00.000Z',
        recorded_at: nowIso,
      })

      const medicationId = crypto.randomUUID()
      store.medications.set(medicationId, {
        id: medicationId,
        hospital_id: hospitalId,
        patient_id: patientId,
        encounter_id: encounterId,
        provenance_id: provenanceId,
        medicine_name: 'Montelukast',
        catalogue_item_id: null,
        statement_type: 'prescribed',
        status: 'active',
        dose: '10 mg once nightly',
        start_at: null,
        end_at: null,
        superseded_by_statement_id: null,
        verification_status: 'verified',
        recorded_at: nowIso,
      })
    }
  })
}
