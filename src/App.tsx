import { type FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ClipboardList,
  Database,
  FilePenLine,
  FileText,
  Keyboard,
  LayoutGrid,
  ListChecks,
  LogOut,
  Mic,
  Moon,
  Plus,
  Printer,
  RotateCcw,
  Search,
  ShieldAlert,
  Square,
  Sun,
  Trash2,
  UserCheck,
} from 'lucide-react'
import './App.css'

type Tab = 'Overview' | 'Briefing' | 'Prescription A4' | 'Personal Notes'
type NavSection = 'Overview' | 'Prescription A4' | 'Personal Notes'
type InputMode = 'voice' | 'written'
type ThemeMode = 'light' | 'dark'
type PersonalFormatMode = 'concise_polish' | 'key_points_summary' | 'manual'

type Patient = {
  id: string
  synthetic_mrn: string
  given_name: string
  family_name: string
  date_of_birth: string
  sex_at_birth: string | null
  identity_status: string
}

type Appointment = {
  id: string
  patient_id: string
  scheduled_at: string
  status: string
}

type Encounter = {
  id: string
  patient_id: string
  status: string
}

type ClinicalRow = {
  id: string
  substance?: string
  reaction?: string | null
  verification_status?: string
  display_name?: string
  status?: string
  test_name?: string | null
  value_text?: string | null
  value_numeric?: string | null
  unit?: string | null
  medicine_name?: string
  dose?: string | null
}

type Session = {
  userId: string
  displayName: string
  roleCode: string
  hospitalId: string
  basicAuth: string
}

type PrescriptionMedicine = {
  medicine_name: string
  strength?: string | null
  dose?: string | null
  route?: string | null
  frequency?: string | null
  duration?: string | null
  quantity?: string | null
  instructions?: string | null
  source_uncertainty?: string | null
}

type AiDraft = {
  chief_complaint: string
  history_of_present_illness: string
  patient_reported_facts: string[]
  doctor_questions: string[]
  examination_findings: string[]
  assessment: string
  plan: string
  missing_information: string[]
  uncertainty: string[]
  medication_candidates: string[]
  prescription_draft: {
    medicines: PrescriptionMedicine[]
    advice: string[]
    follow_up?: string | null
    missing_prescription_information: string[]
  }
}

type ClinicalTemplateState = {
  chiefComplaint: string
  history: string
  patientFacts: string
  doctorQuestions: string
  examination: string
  assessment: string
  plan: string
  missingInformation: string
}

type SpeechRecognitionResultLike = {
  isFinal: boolean
  0: { transcript: string }
}

type SpeechRecognitionEventLike = {
  resultIndex: number
  results: {
    length: number
    [index: number]: SpeechRecognitionResultLike
  }
}

type SpeechRecognitionLike = {
  continuous: boolean
  interimResults: boolean
  lang: string
  start: () => void
  stop: () => void
  onresult: ((event: SpeechRecognitionEventLike) => void) | null
  onerror: ((event: { error: string }) => void) | null
  onend: (() => void) | null
}

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike

const DEMO_EMAIL = 'doctor.synthetic@mediflow.local'
const DEMO_PASSWORD = 'MediFlowDemo123!'
const THEME_STORAGE_KEY = 'mediflow-theme'

const EMPTY_CLINICAL_TEMPLATE: ClinicalTemplateState = {
  chiefComplaint: '',
  history: '',
  patientFacts: '',
  doctorQuestions: '',
  examination: '',
  assessment: 'Draft only — clinician approval required',
  plan: '',
  missingInformation: '',
}

function createEmptyMedicine(): PrescriptionMedicine {
  return {
    medicine_name: '',
    strength: '',
    dose: '',
    route: '',
    frequency: '',
    duration: '',
    quantity: '',
    instructions: '',
    source_uncertainty: '',
  }
}

function getMissingMedicineFields(medicine: PrescriptionMedicine): string[] {
  const missing: string[] = []
  if (!medicine.medicine_name?.trim()) missing.push('medicine name')
  if (!medicine.strength?.trim()) missing.push('strength')
  if (!medicine.dose?.trim()) missing.push('dose')
  if (!medicine.route?.trim()) missing.push('route')
  if (!medicine.frequency?.trim()) missing.push('frequency')
  if (!medicine.duration?.trim()) missing.push('duration')
  if (!medicine.quantity?.trim()) missing.push('quantity')
  return missing
}

function ageFrom(date_of_birth: string) {
  const birth = new Date(`${date_of_birth}T00:00:00`)
  if (Number.isNaN(birth.getTime())) return '—'
  const today = new Date()
  let age = today.getFullYear() - birth.getFullYear()
  if (
    today.getMonth() < birth.getMonth() ||
    (today.getMonth() === birth.getMonth() && today.getDate() < birth.getDate())
  ) {
    age -= 1
  }
  return age
}

function initials(patient: Patient) {
  return `${patient.given_name[0] ?? ''}${patient.family_name[0] ?? ''}`.toUpperCase()
}

function formatTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('en-IN', { hour: '2-digit', minute: '2-digit' }).format(date)
}

function formatDateTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

function greetingForTime() {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 17) return 'Good afternoon'
  return 'Good evening'
}

function getInitialTheme(): ThemeMode {
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY)
    if (stored === 'dark' || stored === 'light') return stored
  } catch {
    // Ignore storage access errors
  }
  return 'light'
}

function App() {
  const [theme, setTheme] = useState<ThemeMode>(getInitialTheme)
  const [session, setSession] = useState<Session | null>(null)
  const [email, setEmail] = useState(DEMO_EMAIL)
  const [password, setPassword] = useState(DEMO_PASSWORD)
  const [loginError, setLoginError] = useState('')
  const [loginBusy, setLoginBusy] = useState(false)
  const [toast, setToast] = useState('')
  const [activeTab, setActiveTab] = useState<Tab>('Prescription A4')
  const [activeNav, setActiveNav] = useState<NavSection>('Prescription A4')
  const [patients, setPatients] = useState<Patient[]>([])
  const [selectedPatientId, setSelectedPatientId] = useState('')
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [encounters, setEncounters] = useState<Encounter[]>([])
  const [conditions, setConditions] = useState<ClinicalRow[]>([])
  const [allergies, setAllergies] = useState<ClinicalRow[]>([])
  const [observations, setObservations] = useState<ClinicalRow[]>([])
  const [medications, setMedications] = useState<ClinicalRow[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')

  // Feature 1: Consultation Input + Live Editable Hospital A4 Sheet
  const [consultInputMode, setConsultInputMode] = useState<InputMode>('voice')
  const [liveTranscript, setLiveTranscript] = useState('')
  const [consultAudioUrl, setConsultAudioUrl] = useState('')
  const [draftLoading, setDraftLoading] = useState(false)
  const [aiDraft, setAiDraft] = useState<AiDraft | null>(null)
  const [clinicalTemplate, setClinicalTemplate] = useState<ClinicalTemplateState>(EMPTY_CLINICAL_TEMPLATE)
  const [clinicalNoteStatus, setClinicalNoteStatus] = useState<'none' | 'saved' | 'approved'>('none')
  const [clinicalDraftId, setClinicalDraftId] = useState('')

  const [prescriptionDraftEdits, setPrescriptionDraftEdits] = useState<PrescriptionMedicine[]>([])
  const [adviceText, setAdviceText] = useState('')
  const [followUpText, setFollowUpText] = useState('')
  const [prescriptionStatus, setPrescriptionStatus] = useState<'none' | 'created' | 'approved' | 'signed'>('none')
  const [prescriptionDraftId, setPrescriptionDraftId] = useState('')
  const [signedPrescriptionRef, setSignedPrescriptionRef] = useState('')
  const [signedAt, setSignedAt] = useState('')
  const [prescriptionSafetyWarnings, setPrescriptionSafetyWarnings] = useState<string[]>([])

  // Feature 2: Personal Patient Notes (Voice / Written + Adaptive Point-Wise AI)
  const [personalInputMode, setPersonalInputMode] = useState<InputMode>('written')
  const [personalRawText, setPersonalRawText] = useState('')
  const [personalAudioUrl, setPersonalAudioUrl] = useState('')
  const [personalTitle, setPersonalTitle] = useState('Patient Care Instructions')
  const [personalPoints, setPersonalPoints] = useState<string[]>([])
  const [personalFormatMode, setPersonalFormatMode] = useState<PersonalFormatMode>('manual')
  const [personalSpellingNote, setPersonalSpellingNote] = useState('')
  const [personalUncertainties, setPersonalUncertainties] = useState<string[]>([])
  const [personalLoading, setPersonalLoading] = useState(false)
  const [personalNoteId, setPersonalNoteId] = useState('')
  const [personalNoteStatus, setPersonalNoteStatus] = useState<'none' | 'saved' | 'approved'>('none')
  const [includePersonalNotesOnA4, setIncludePersonalNotesOnA4] = useState(true)

  // Shared browser audio capture controller (tracks which target is actively recording)
  const [recordingTarget, setRecordingTarget] = useState<'consult' | 'personal' | null>(null)
  const speechRecognitionRef = useRef<SpeechRecognitionLike | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)

  const [printDate] = useState(() =>
    new Intl.DateTimeFormat('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    }).format(new Date()),
  )
  const queueInterval = useRef<number | null>(null)
  const toastTimer = useRef<number | null>(null)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, theme)
    } catch {
      // Ignore storage access errors
    }
  }, [theme])

  useEffect(() => {
    return () => {
      if (queueInterval.current) window.clearInterval(queueInterval.current)
      if (toastTimer.current) window.clearTimeout(toastTimer.current)
      speechRecognitionRef.current?.stop()
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop()
      }
    }
  }, [])

  function toggleTheme() {
    setTheme((current) => (current === 'light' ? 'dark' : 'light'))
  }

  const selectedPatient = useMemo(
    () => patients.find((patient) => patient.id === selectedPatientId) ?? patients[0],
    [patients, selectedPatientId],
  )

  const selectedAppointment = useMemo(
    () => appointments.find((appointment) => appointment.patient_id === selectedPatient?.id),
    [appointments, selectedPatient],
  )

  const selectedEncounter = useMemo(
    () => encounters.find((encounter) => encounter.patient_id === selectedPatient?.id),
    [encounters, selectedPatient],
  )

  function headers(current: Session) {
    return {
      Authorization: `Basic ${current.basicAuth}`,
      'X-Hospital-Id': current.hospitalId,
      'X-Mediflow-Purpose': 'academic synthetic clinical demonstration',
    }
  }

  function notify(message: string) {
    setToast(message)
    if (toastTimer.current) window.clearTimeout(toastTimer.current)
    toastTimer.current = window.setTimeout(() => setToast(''), 3500)
  }

  function revokeAudio(setter: (fn: (current: string) => string) => void) {
    setter((current) => {
      if (current) URL.revokeObjectURL(current)
      return ''
    })
  }

  function stopVoiceCapture() {
    speechRecognitionRef.current?.stop()
    speechRecognitionRef.current = null
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop()
    }
    mediaRecorderRef.current = null
    setRecordingTarget(null)
  }

  async function startVoiceCapture(target: 'consult' | 'personal') {
    if (recordingTarget) {
      stopVoiceCapture()
    }

    const browserWindow = window as typeof window & {
      SpeechRecognition?: SpeechRecognitionConstructor
      webkitSpeechRecognition?: SpeechRecognitionConstructor
    }

    let recorderStarted = false
    try {
      const stream = await navigator.mediaDevices?.getUserMedia({ audio: true })
      if (stream && 'MediaRecorder' in window) {
        const recorder = new MediaRecorder(stream)
        const chunks: Blob[] = []
        recorder.ondataavailable = (event) => {
          if (event.data.size > 0) chunks.push(event.data)
        }
        recorder.onstop = () => {
          const blob = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' })
          const setUrl = target === 'consult' ? setConsultAudioUrl : setPersonalAudioUrl
          setUrl((current) => {
            if (current) URL.revokeObjectURL(current)
            return URL.createObjectURL(blob)
          })
          stream.getTracks().forEach((track) => track.stop())
        }
        recorder.start()
        mediaRecorderRef.current = recorder
        recorderStarted = true
      }
    } catch {
      notify('Microphone permission was not granted. Switch to Written input or type directly.')
    }

    const Recognition = browserWindow.SpeechRecognition ?? browserWindow.webkitSpeechRecognition
    if (!Recognition) {
      if (recorderStarted) {
        setRecordingTarget(target)
        notify('Recording local audio preview. Live browser speech-to-text is unavailable; type or paste text below.')
      } else {
        notify('Browser speech recognition is unavailable. Use Written input to type or paste.')
      }
      return
    }

    const recognition = new Recognition()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'en-IN'
    recognition.onresult = (event) => {
      let finalizedAddition = ''
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index]
        if (result.isFinal) finalizedAddition += `${result[0].transcript.trim()} `
      }
      const trimmed = finalizedAddition.trim()
      if (!trimmed) return

      if (target === 'consult') {
        setLiveTranscript((current) => (current.trim() ? `${current.trim()} ${trimmed}` : trimmed))
        setClinicalNoteStatus((status) => (status !== 'none' ? 'none' : status))
        setClinicalDraftId('')
      } else {
        setPersonalRawText((current) => (current.trim() ? `${current.trim()} ${trimmed}` : trimmed))
      }
    }
    recognition.onerror = (event) => {
      setRecordingTarget(null)
      notify(`Voice capture error: ${event.error}`)
    }
    recognition.onend = () => {
      setRecordingTarget(null)
    }
    speechRecognitionRef.current = recognition
    recognition.start()
    setRecordingTarget(target)
  }

  function clearConsultationState() {
    setLiveTranscript('')
    setAiDraft(null)
    setClinicalTemplate({ ...EMPTY_CLINICAL_TEMPLATE })
    setClinicalDraftId('')
    setClinicalNoteStatus('none')
    setPrescriptionDraftEdits([])
    setAdviceText('')
    setFollowUpText('')
    setPrescriptionDraftId('')
    setPrescriptionStatus('none')
    setSignedPrescriptionRef('')
    setSignedAt('')
    setPrescriptionSafetyWarnings([])
    revokeAudio(setConsultAudioUrl)
  }

  function clearPersonalNotesState() {
    setPersonalRawText('')
    setPersonalTitle('Patient Care Instructions')
    setPersonalPoints([])
    setPersonalFormatMode('manual')
    setPersonalSpellingNote('')
    setPersonalUncertainties([])
    setPersonalNoteId('')
    setPersonalNoteStatus('none')
    revokeAudio(setPersonalAudioUrl)
  }

  function updateClinicalField(field: keyof ClinicalTemplateState, value: string) {
    setClinicalTemplate((current) => ({ ...current, [field]: value }))
    if (clinicalNoteStatus !== 'none') {
      setClinicalNoteStatus('none')
      setClinicalDraftId('')
    }
  }

  function markPrescriptionEdited() {
    if (prescriptionStatus !== 'none') {
      setPrescriptionStatus('none')
      setPrescriptionDraftId('')
      setSignedPrescriptionRef('')
      setSignedAt('')
      setPrescriptionSafetyWarnings([])
    }
  }

  function updateMedicineField(
    index: number,
    field: keyof PrescriptionMedicine,
    value: string,
  ) {
    setPrescriptionDraftEdits((rows) =>
      rows.map((row, rowIndex) => (rowIndex === index ? { ...row, [field]: value } : row)),
    )
    markPrescriptionEdited()
  }

  function addMedicineRow() {
    setPrescriptionDraftEdits((rows) => [...rows, createEmptyMedicine()])
    markPrescriptionEdited()
  }

  function removeMedicineRow(index: number) {
    setPrescriptionDraftEdits((rows) => rows.filter((_, rowIndex) => rowIndex !== index))
    markPrescriptionEdited()
  }

  function markPersonalNotesEdited() {
    if (personalNoteStatus !== 'none') {
      setPersonalNoteStatus('none')
      setPersonalNoteId('')
    }
  }

  function updatePersonalPoint(index: number, value: string) {
    setPersonalPoints((rows) => rows.map((row, rowIndex) => (rowIndex === index ? value : row)))
    markPersonalNotesEdited()
  }

  function addPersonalPoint() {
    setPersonalPoints((rows) => [...rows, ''])
    markPersonalNotesEdited()
  }

  function removePersonalPoint(index: number) {
    setPersonalPoints((rows) => rows.filter((_, rowIndex) => rowIndex !== index))
    markPersonalNotesEdited()
  }

  async function login(event?: FormEvent) {
    event?.preventDefault()
    setLoginBusy(true)
    setLoginError('')
    try {
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      if (!response.ok) {
        setLoginError('Invalid credentials or backend unavailable.')
        return
      }
      const body = await response.json()
      const assignment = body.assignments?.[0]
      if (!assignment) {
        setLoginError('No active hospital assignment was returned.')
        return
      }
      const nextSession: Session = {
        userId: body.user_id,
        displayName: body.display_name,
        roleCode: assignment.role_code,
        hospitalId: assignment.hospital_id,
        basicAuth: btoa(`${email}:${password}`),
      }
      setSession(nextSession)
      void loadWorkspace(nextSession, false)
      if (queueInterval.current) window.clearInterval(queueInterval.current)
      queueInterval.current = window.setInterval(() => {
        void loadWorkspace(nextSession, true)
      }, 15000)
    } catch {
      setLoginError('Could not connect to the local MediFlow backend.')
    } finally {
      setLoginBusy(false)
    }
  }

  async function loadWorkspace(current: Session, silent = false) {
    if (!silent) setLoading(true)
    try {
      const requestHeaders = headers(current)
      const [patientResponse, appointmentResponse, encounterResponse] = await Promise.all([
        fetch('/api/v1/patients?limit=100', { headers: requestHeaders }),
        fetch('/api/v1/appointments', { headers: requestHeaders }),
        fetch('/api/v1/encounters', { headers: requestHeaders }),
      ])
      if (!patientResponse.ok || !appointmentResponse.ok || !encounterResponse.ok) {
        throw new Error('The local workspace returned an authorization or server error.')
      }
      const patientRows: Patient[] = await patientResponse.json()
      setPatients(patientRows)
      setAppointments(await appointmentResponse.json())
      setEncounters(await encounterResponse.json())

      if (!silent) {
        const initialPatient = patientRows[0]
        setSelectedPatientId(initialPatient?.id ?? '')
        if (initialPatient) {
          void loadClinicalRecords(current, initialPatient.id)
          void loadClinicalTemplate(current, initialPatient.id)
          void loadPersonalNotes(current, initialPatient.id)
        }
      }
    } catch (error) {
      if (!silent) {
        notify(error instanceof Error ? error.message : 'Could not load workspace.')
      }
    } finally {
      if (!silent) setLoading(false)
    }
  }

  async function loadClinicalRecords(current: Session, patientId: string) {
    if (!patientId) return
    const requestHeaders = headers(current)
    const suffix = `?patient_id=${encodeURIComponent(patientId)}`
    const [conditionResponse, allergyResponse, observationResponse, medicationResponse] = await Promise.all([
      fetch(`/api/v1/conditions${suffix}`, { headers: requestHeaders }),
      fetch(`/api/v1/allergies${suffix}`, { headers: requestHeaders }),
      fetch(`/api/v1/observations${suffix}`, { headers: requestHeaders }),
      fetch(`/api/v1/medications${suffix}`, { headers: requestHeaders }),
    ])
    setConditions(conditionResponse.ok ? await conditionResponse.json() : [])
    setAllergies(allergyResponse.ok ? await allergyResponse.json() : [])
    setObservations(observationResponse.ok ? await observationResponse.json() : [])
    setMedications(medicationResponse.ok ? await medicationResponse.json() : [])
  }

  async function loadClinicalTemplate(current: Session, patientId: string) {
    const response = await fetch(
      `/api/v1/clinical-notes/drafts?patient_id=${encodeURIComponent(patientId)}`,
      { headers: headers(current) },
    )
    if (!response.ok) return
    const rows = await response.json()
    const latest = rows[0]
    if (!latest) return
    setClinicalDraftId(latest.status === 'draft' ? latest.id : '')
    setClinicalNoteStatus(
      latest.status === 'approved' ? 'approved' : latest.status === 'draft' ? 'saved' : 'none',
    )
    setClinicalTemplate({
      chiefComplaint: latest.chief_complaint,
      history: latest.history,
      patientFacts: latest.patient_facts,
      doctorQuestions: latest.doctor_questions,
      examination: latest.examination_findings,
      assessment: latest.assessment,
      plan: latest.plan,
      missingInformation: latest.missing_information,
    })
    setLiveTranscript(latest.transcript_text || '')
  }

  async function loadPersonalNotes(current: Session, patientId: string) {
    const response = await fetch(
      `/api/v1/personal-notes?patient_id=${encodeURIComponent(patientId)}`,
      { headers: headers(current) },
    )
    if (!response.ok) return
    const rows = await response.json()
    const latest = rows[0]
    if (!latest) return
    setPersonalNoteId(latest.status === 'draft' ? latest.id : '')
    setPersonalNoteStatus(
      latest.status === 'approved' ? 'approved' : latest.status === 'draft' ? 'saved' : 'none',
    )
    setPersonalTitle(latest.title || 'Patient Care Instructions')
    setPersonalPoints(Array.isArray(latest.bullet_points) ? latest.bullet_points : [])
    setPersonalRawText(latest.raw_input_text || '')
    setPersonalFormatMode(latest.format_mode || 'manual')
  }

  async function checkInPatient() {
    if (!session || !selectedAppointment) {
      notify('No appointment is linked to the selected patient.')
      return
    }
    const response = await fetch(`/api/v1/appointments/${selectedAppointment.id}/status`, {
      method: 'PATCH',
      headers: { ...headers(session), 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'checked_in' }),
    })
    if (!response.ok) {
      notify('The appointment status update was rejected.')
      return
    }
    setAppointments((rows) =>
      rows.map((row) => (row.id === selectedAppointment.id ? { ...row, status: 'checked_in' } : row)),
    )
    notify('Patient appointment marked checked in.')
  }

  function selectPatient(patient: Patient) {
    if (recordingTarget) stopVoiceCapture()
    setSelectedPatientId(patient.id)
    clearConsultationState()
    clearPersonalNotesState()
    if (session) {
      void loadClinicalRecords(session, patient.id)
      void loadClinicalTemplate(session, patient.id)
      void loadPersonalNotes(session, patient.id)
    }
  }

  function selectNavigation(label: NavSection) {
    setActiveNav(label)
    setActiveTab(label)
  }

  async function analyzeAndFillA4() {
    if (!session || !selectedPatient) return
    if (!liveTranscript.trim()) {
      notify('Record voice or type the consultation text first.')
      return
    }
    setDraftLoading(true)
    setAiDraft(null)
    try {
      const response = await fetch('/api/v1/ai/clinical-draft', {
        method: 'POST',
        headers: { ...headers(session), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          patient_id: selectedPatient.id,
          encounter_id: selectedEncounter?.id ?? null,
          transcript: liveTranscript,
          manual_text: [
            `Chief complaint: ${clinicalTemplate.chiefComplaint}`,
            `History: ${clinicalTemplate.history}`,
            `Patient-reported facts: ${clinicalTemplate.patientFacts}`,
            `Doctor questions: ${clinicalTemplate.doctorQuestions}`,
            `Examination findings: ${clinicalTemplate.examination}`,
            `Assessment: ${clinicalTemplate.assessment}`,
            `Plan: ${clinicalTemplate.plan}`,
            `Missing information: ${clinicalTemplate.missingInformation}`,
          ].join('\n'),
        }),
      })
      const body = await response.json()
      if (!response.ok) {
        notify(body.detail ?? 'AI auto-fill failed.')
        return
      }
      const draft: AiDraft = body.draft
      setAiDraft(draft)
      setClinicalNoteStatus('none')
      setClinicalDraftId('')
      setPrescriptionStatus('none')
      setPrescriptionDraftId('')
      setSignedPrescriptionRef('')
      setSignedAt('')
      setPrescriptionSafetyWarnings([])

      setPrescriptionDraftEdits(
        (draft.prescription_draft?.medicines ?? []).map((medicine: PrescriptionMedicine) => ({
          medicine_name: medicine.medicine_name || '',
          strength: medicine.strength ?? '',
          dose: medicine.dose ?? '',
          route: medicine.route ?? '',
          frequency: medicine.frequency ?? '',
          duration: medicine.duration ?? '',
          quantity: medicine.quantity ?? '',
          instructions: medicine.instructions ?? '',
          source_uncertainty: medicine.source_uncertainty ?? '',
        })),
      )
      setAdviceText((draft.prescription_draft?.advice ?? []).join('\n'))
      setFollowUpText(draft.prescription_draft?.follow_up ?? '')
      setClinicalTemplate({
        chiefComplaint: draft.chief_complaint || '',
        history: draft.history_of_present_illness || '',
        patientFacts: draft.patient_reported_facts?.join('\n') || '',
        doctorQuestions: draft.doctor_questions?.join('\n') || '',
        examination: draft.examination_findings?.join('\n') || '',
        assessment: draft.assessment || 'Draft only — clinician approval required',
        plan: draft.plan || '',
        missingInformation: [
          ...(draft.missing_information || []),
          ...(draft.uncertainty || []),
          ...(draft.prescription_draft?.missing_prescription_information || []),
        ].join('\n'),
      })
      notify('Hospital A4 sheet auto-filled. Click any field on the sheet to edit before approving.')
    } catch {
      notify('AI service could not be reached.')
    } finally {
      setDraftLoading(false)
    }
  }

  async function saveClinicalDraft() {
    if (!session || !selectedPatient || !selectedEncounter) {
      notify('A linked encounter is required.')
      return
    }
    const chiefComplaint = clinicalTemplate.chiefComplaint.trim() || 'Pending clinician review'
    const response = await fetch('/api/v1/clinical-notes/drafts', {
      method: 'POST',
      headers: { ...headers(session), 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_id: selectedPatient.id,
        encounter_id: selectedEncounter.id,
        transcript_text: liveTranscript.trim() || 'Manual A4 sheet entry.',
        chief_complaint: chiefComplaint,
        history: clinicalTemplate.history,
        patient_facts: clinicalTemplate.patientFacts,
        doctor_questions: clinicalTemplate.doctorQuestions,
        examination_findings: clinicalTemplate.examination,
        assessment: clinicalTemplate.assessment,
        plan: clinicalTemplate.plan,
        missing_information: clinicalTemplate.missingInformation,
      }),
    })
    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}))
      notify(errorBody.detail ?? 'Clinical record draft could not be saved.')
      return
    }
    const draft = await response.json()
    setClinicalDraftId(draft.id)
    setClinicalNoteStatus('saved')
    notify('Clinical note saved as ClinicalNoteDraft.')
  }

  async function approveClinicalDraft() {
    if (!session || !clinicalDraftId) return
    const response = await fetch(`/api/v1/clinical-notes/drafts/${clinicalDraftId}/approval`, {
      method: 'PATCH',
      headers: { ...headers(session), 'Content-Type': 'application/json' },
      body: JSON.stringify({ approved: true }),
    })
    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}))
      notify(errorBody.detail ?? 'Clinical record approval was rejected.')
      return
    }
    setClinicalDraftId('')
    setClinicalNoteStatus('approved')
    notify('Clinical record approved by clinician.')
  }

  async function createPrescriptionDraft() {
    if (!session || !selectedPatient || !selectedEncounter) {
      notify('A linked encounter is required.')
      return
    }
    const populatedLines = prescriptionDraftEdits
      .filter((medicine) => medicine.medicine_name.trim().length > 0)
      .map((medicine) => ({
        medicine_name: medicine.medicine_name.trim(),
        strength: medicine.strength?.trim() || null,
        dose: medicine.dose?.trim() || null,
        route: medicine.route?.trim() || null,
        frequency: medicine.frequency?.trim() || null,
        duration: medicine.duration?.trim() || null,
        quantity: medicine.quantity?.trim() || null,
        instructions: medicine.instructions?.trim() || null,
      }))

    if (populatedLines.length === 0) {
      notify('Add at least one medicine on the A4 sheet before creating a prescription draft.')
      return
    }

    const response = await fetch('/api/v1/prescription-drafts', {
      method: 'POST',
      headers: { ...headers(session), 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_id: selectedPatient.id,
        encounter_id: selectedEncounter.id,
        lines: populatedLines,
      }),
    })
    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}))
      notify(errorBody.detail ?? 'The prescription draft could not be created.')
      return
    }
    const draft = await response.json()
    setPrescriptionDraftId(draft.id)
    setPrescriptionStatus('created')
    setSignedPrescriptionRef('')
    setSignedAt('')
    setPrescriptionSafetyWarnings(Array.isArray(draft.safety_warnings) ? draft.safety_warnings : [])
    notify('Prescription draft created. Review safety warnings and approve before signing.')
  }

  async function approvePrescriptionDraft() {
    if (!session || !prescriptionDraftId) return
    const response = await fetch(`/api/v1/prescription-drafts/${prescriptionDraftId}/approval`, {
      method: 'PATCH',
      headers: { ...headers(session), 'Content-Type': 'application/json' },
      body: JSON.stringify({ approved: true }),
    })
    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}))
      notify(errorBody.detail ?? 'The prescription draft approval was rejected.')
      return
    }
    setPrescriptionStatus('approved')
    notify('Prescription draft approved. Ready for local synthetic signature.')
  }

  async function signPrescriptionDraft() {
    if (!session || !prescriptionDraftId) return
    const response = await fetch(`/api/v1/prescriptions?draft_id=${encodeURIComponent(prescriptionDraftId)}`, {
      method: 'POST',
      headers: { ...headers(session), 'Content-Type': 'application/json' },
      body: JSON.stringify({ signature_reference: 'ACADEMIC-SYNTHETIC-SIGNATURE' }),
    })
    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}))
      notify(errorBody.detail ?? 'Only an approved prescription draft can be signed.')
      return
    }
    const signed = await response.json()
    setPrescriptionStatus('signed')
    setSignedPrescriptionRef(signed.signature_reference || 'ACADEMIC-SYNTHETIC-SIGNATURE')
    setSignedAt(signed.signed_at || new Date().toISOString())
    notify('Local synthetic signature recorded (not a real prescription).')
  }

  // Feature 2: Adaptive AI Personal Patient Notes Formatting & Approval
  async function formatPersonalNotesWithAI() {
    if (!session || !selectedPatient) return
    if (!personalRawText.trim()) {
      notify('Record voice or type personal notes first.')
      return
    }
    setPersonalLoading(true)
    try {
      const response = await fetch('/api/v1/ai/personal-notes', {
        method: 'POST',
        headers: { ...headers(session), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          patient_id: selectedPatient.id,
          encounter_id: selectedEncounter?.id ?? null,
          raw_text: personalRawText,
          input_mode: personalInputMode,
        }),
      })
      const body = await response.json()
      if (!response.ok) {
        notify(body.detail ?? 'Personal notes AI formatting failed.')
        return
      }
      const formatted = body.notes
      setPersonalTitle(formatted.title || 'Patient Care Instructions')
      setPersonalPoints(Array.isArray(formatted.bullet_points) ? formatted.bullet_points : [])
      setPersonalFormatMode(
        formatted.mode_applied === 'key_points_summary' ? 'key_points_summary' : 'concise_polish',
      )
      setPersonalSpellingNote(formatted.spelling_corrections_note || '')
      setPersonalUncertainties(Array.isArray(formatted.uncertainties) ? formatted.uncertainties : [])
      setPersonalNoteStatus('none')
      setPersonalNoteId('')
      notify(
        formatted.mode_applied === 'key_points_summary'
          ? 'Long input condensed into main patient points. Review and edit before approving.'
          : 'Spelling polished and formatted point-wise. Review and edit before approving.',
      )
    } catch {
      notify('Personal notes AI service could not be reached.')
    } finally {
      setPersonalLoading(false)
    }
  }

  async function savePersonalNotesDraft() {
    if (!session || !selectedPatient) return
    const cleanedPoints = personalPoints.map((point) => point.trim()).filter(Boolean)
    if (cleanedPoints.length === 0) {
      notify('Format with AI or add at least one bullet point before saving.')
      return
    }
    const response = await fetch('/api/v1/personal-notes', {
      method: 'POST',
      headers: { ...headers(session), 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_id: selectedPatient.id,
        encounter_id: selectedEncounter?.id ?? null,
        raw_input_text: personalRawText,
        input_mode: personalInputMode,
        format_mode: personalFormatMode,
        title: personalTitle.trim() || 'Patient Care Instructions',
        bullet_points: cleanedPoints,
      }),
    })
    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}))
      notify(errorBody.detail ?? 'Personal notes could not be saved.')
      return
    }
    const draft = await response.json()
    setPersonalNoteId(draft.id)
    setPersonalNoteStatus('saved')
    notify('Personal patient notes saved as draft. Click Approve to finalize.')
  }

  async function approvePersonalNotes() {
    if (!session || !personalNoteId) return
    const response = await fetch(`/api/v1/personal-notes/${personalNoteId}/approval`, {
      method: 'PATCH',
      headers: { ...headers(session), 'Content-Type': 'application/json' },
      body: JSON.stringify({ approved: true }),
    })
    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}))
      notify(errorBody.detail ?? 'Personal notes approval was rejected.')
      return
    }
    setPersonalNoteId('')
    setPersonalNoteStatus('approved')
    notify('Personal patient notes approved by clinician.')
  }

  function printDocument(target: 'a4' | 'personal-notes') {
    document.body.dataset.printTarget = target
    window.print()
    window.setTimeout(() => delete document.body.dataset.printTarget, 250)
  }

  if (!session) {
    return (
      <main className="login-shell">
        <section className="login-art">
          <div className="login-brand">
            <span className="brand-symbol">M</span>
            <span className="brand-wordmark">
              MediFlow <span>AI</span>
            </span>
          </div>
          <div className="login-hero">
            <span className="login-kicker">Academic Clinical Workspace · Synthetic Data</span>
            <h1>
              Speak or type.
              <br />
              <em>Auto-fill A4.</em>
            </h1>
            <p>
              Voice and written consultation inputs that populate your editable Hospital A4 prescription sheet and point-wise Personal Patient Notes.
            </p>
            <div className="login-metrics">
              <div>
                <strong>03</strong>
                <span>Synthetic patients</span>
              </div>
              <div>
                <strong>00</strong>
                <span>Autonomous approvals</span>
              </div>
              <div>
                <strong>100%</strong>
                <span>Clinician-controlled</span>
              </div>
            </div>
          </div>
        </section>

        <section className="login-panel">
          <button
            type="button"
            className="theme-toggle-btn login-theme-toggle"
            onClick={toggleTheme}
            aria-label={theme === 'light' ? 'Switch to dark studio mode' : 'Switch to light studio mode'}
          >
            {theme === 'light' ? <Moon size={16} strokeWidth={1.85} /> : <Sun size={16} strokeWidth={1.85} />}
            <span>{theme === 'light' ? 'Dark studio' : 'Light studio'}</span>
          </button>

          <form className="login-card" onSubmit={(event) => void login(event)}>
            <div className="login-eyebrow">Local synthetic hospital · SYN-001</div>
            <h2>Welcome back</h2>
            <p>Sign in with your clinician credentials to open the workspace.</p>
            <label className="login-field">
              <span>Email address</span>
              <input
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="username"
              />
            </label>
            <label className="login-field">
              <span>Password</span>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
              />
            </label>
            {loginError && <div className="login-error">{loginError}</div>}
            <button className="sign-in-button" type="submit" disabled={loginBusy}>
              <span>{loginBusy ? 'Signing in…' : 'Enter workspace'}</span>
              <ArrowRight size={18} strokeWidth={2} />
            </button>
            <div className="login-safety">
              Synthetic academic data · Not for real clinical diagnosis or prescribing
            </div>
          </form>
        </section>
      </main>
    )
  }

  const filteredPatients = patients.filter((patient) => {
    const query = search.trim().toLowerCase()
    if (!query) return true
    return `${patient.given_name} ${patient.family_name} ${patient.synthetic_mrn}`.toLowerCase().includes(query)
  })

  const clinicalNoteStatusLabel =
    clinicalNoteStatus === 'approved'
      ? 'Clinical record approved'
      : clinicalNoteStatus === 'saved'
        ? 'Clinical draft saved'
        : 'Clinical draft unapproved'

  const prescriptionStatusLabel =
    prescriptionStatus === 'signed'
      ? 'Synthetic signature added'
      : prescriptionStatus === 'approved'
        ? 'Prescription approved'
        : prescriptionStatus === 'created'
          ? 'Prescription draft created'
          : 'Not signed'

  const personalStatusLabel =
    personalNoteStatus === 'approved'
      ? 'Approved by clinician'
      : personalNoteStatus === 'saved'
        ? 'Saved draft'
        : 'Draft · Not approved'

  const personalModeLabel =
    personalFormatMode === 'key_points_summary'
      ? 'Long conversation summarized into main points'
      : personalFormatMode === 'concise_polish'
        ? 'Short note spelling polished & formatted point-wise'
        : 'Manual clinician entry'

  const formattedAdvice = adviceText
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)

  const activePersonalPoints = personalPoints.map((point) => point.trim()).filter(Boolean)

  return (
    <main className="dashboard">
      {toast && <div className="toast" role="status">{toast}</div>}

      <aside className="sidebar">
        <div className="brand">
          <span className="brand-symbol">M</span>
          <span className="brand-wordmark">
            MediFlow <span>AI</span>
          </span>
        </div>

        <nav className="sidebar-nav" aria-label="Workspace navigation">
          <button
            type="button"
            className={activeNav === 'Overview' ? 'nav-link active' : 'nav-link'}
            onClick={() => selectNavigation('Overview')}
            title="Overview"
          >
            <span className="nav-icon-wrap">
              <LayoutGrid size={18} strokeWidth={1.85} />
            </span>
            <span className="nav-label">Overview</span>
          </button>

          <button
            type="button"
            className={activeNav === 'Prescription A4' ? 'nav-link active' : 'nav-link'}
            onClick={() => selectNavigation('Prescription A4')}
            title="Prescription A4"
          >
            <span className="nav-icon-wrap">
              <ClipboardList size={18} strokeWidth={1.85} />
            </span>
            <span className="nav-label">Prescription A4</span>
            <span className="nav-count">{patients.length}</span>
          </button>

          <button
            type="button"
            className={activeNav === 'Personal Notes' ? 'nav-link active' : 'nav-link'}
            onClick={() => selectNavigation('Personal Notes')}
            title="Personal Notes"
          >
            <span className="nav-icon-wrap">
              <ListChecks size={18} strokeWidth={1.85} />
            </span>
            <span className="nav-label">Personal Notes</span>
          </button>
        </nav>

        <div className="sidebar-bottom">
          <button
            type="button"
            className="theme-toggle-btn"
            onClick={toggleTheme}
            title={theme === 'light' ? 'Switch to dark studio mode' : 'Switch to light studio mode'}
          >
            {theme === 'light' ? <Moon size={16} strokeWidth={1.85} /> : <Sun size={16} strokeWidth={1.85} />}
            <span className="theme-label">{theme === 'light' ? 'Dark studio' : 'Light studio'}</span>
          </button>

          <div className="doctor-profile">
            <span className="doctor-avatar">
              {session.displayName.split(' ').map((word) => word[0]).slice(-2).join('')}
            </span>
            <div className="doctor-meta">
              <strong>{session.displayName}</strong>
              <small>{session.roleCode}</small>
            </div>
            <button
              type="button"
              className="exit-button"
              aria-label="Sign out"
              title="Sign out"
              onClick={() => {
                if (queueInterval.current) window.clearInterval(queueInterval.current)
                stopVoiceCapture()
                revokeAudio(setConsultAudioUrl)
                revokeAudio(setPersonalAudioUrl)
                setSession(null)
              }}
            >
              <LogOut size={16} strokeWidth={1.85} />
            </button>
          </div>
        </div>
      </aside>

      <section className="main">
        <header className="header">
          <div className="header-title-block">
            <span className="date-label">MediFlow Synthetic Hospital · {printDate}</span>
            <h1>{greetingForTime()}, {session.displayName}</h1>
          </div>
          <div className="header-actions">
            <label className="search-button">
              <Search size={16} strokeWidth={1.85} />
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search name or MRN"
              />
            </label>
            <button type="button" className="primary-button" onClick={checkInPatient}>
              <UserCheck size={16} strokeWidth={2} />
              <span>Check in patient</span>
            </button>
          </div>
        </header>

        {loading ? (
          <div className="loading-state">Loading verified clinical workspace…</div>
        ) : (
          <div className="workspace-grid">
            <section className="queue-card" aria-label="Patient queue">
              <div className="panel-heading">
                <div>
                  <span className="panel-kicker">Clinical Queue</span>
                  <h2>Waiting patients</h2>
                </div>
                <small>{filteredPatients.length} total</small>
              </div>

              <div className="patient-list">
                {filteredPatients.map((patient) => {
                  const appointment = appointments.find((row) => row.patient_id === patient.id)
                  const isSelected = selectedPatient?.id === patient.id
                  return (
                    <button
                      type="button"
                      className={isSelected ? 'patient-row selected' : 'patient-row'}
                      onClick={() => selectPatient(patient)}
                      key={patient.id}
                    >
                      <span className="patient-avatar">{initials(patient)}</span>
                      <span className="patient-info">
                        <strong>{patient.given_name} {patient.family_name}</strong>
                        <small>{ageFrom(patient.date_of_birth)} yrs · {patient.synthetic_mrn}</small>
                        <span className="patient-visit-status">
                          {appointment?.status?.replace('_', ' ') ?? 'not scheduled'}
                        </span>
                      </span>
                      <span className="patient-time-col">
                        <span className="wait-time">
                          {appointment ? formatTime(appointment.scheduled_at) : '—'}
                        </span>
                      </span>
                    </button>
                  )
                })}
                {filteredPatients.length === 0 && (
                  <div className="empty-state">No synthetic patient matches this search.</div>
                )}
              </div>
            </section>

            {selectedPatient ? (
              <section className="patient-card" aria-label="Selected patient workspace">
                <div className="patient-card-header">
                  <div className="patient-identity">
                    <span className="large-avatar">{initials(selectedPatient)}</span>
                    <div className="patient-identity-text">
                      <span className="patient-identity-kicker">Selected Patient</span>
                      <h2>{selectedPatient.given_name} {selectedPatient.family_name}</h2>
                      <div className="patient-identity-meta">
                        <span>{ageFrom(selectedPatient.date_of_birth)} yrs</span>
                        <span aria-hidden="true">·</span>
                        <span>{selectedPatient.sex_at_birth ?? 'Sex not recorded'}</span>
                        <span aria-hidden="true">·</span>
                        <span className="meta-mono">{selectedPatient.synthetic_mrn}</span>
                        {selectedEncounter && (
                          <>
                            <span aria-hidden="true">·</span>
                            <span>Encounter: {selectedEncounter.status}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="identity-status-text">
                    <CheckCircle2 size={16} strokeWidth={2} />
                    <span>{selectedPatient.identity_status}</span>
                  </div>
                </div>

                <div className="tabs" role="tablist">
                  {(['Overview', 'Briefing', 'Prescription A4', 'Personal Notes'] as Tab[]).map((tab) => (
                    <button
                      type="button"
                      role="tab"
                      aria-selected={activeTab === tab}
                      className={activeTab === tab ? 'active' : ''}
                      onClick={() => {
                        setActiveTab(tab)
                        if (tab === 'Overview' || tab === 'Prescription A4' || tab === 'Personal Notes') {
                          setActiveNav(tab)
                        }
                      }}
                      key={tab}
                    >
                      {tab}
                    </button>
                  ))}
                </div>

                {/* --- Tab 1: Overview --- */}
                {activeTab === 'Overview' && (
                  <div className="tab-content">
                    <div className="content-heading">
                      <div>
                        <span className="content-kicker">Structured Summary</span>
                        <h3>Patient overview</h3>
                      </div>
                      <span className="status-label">
                        <Database size={14} strokeWidth={1.9} />
                        Backend-verified
                      </span>
                    </div>

                    <div className="overview-grid">
                      <div className="overview-card">
                        <div className="overview-card-top">
                          <small>Allergies</small>
                          <ShieldAlert size={18} strokeWidth={1.9} className="overview-icon-danger" />
                        </div>
                        <strong>{allergies[0]?.substance ?? 'No records'}</strong>
                        <p>{allergies[0]?.reaction ?? 'No recorded reaction'}</p>
                      </div>

                      <div className="overview-card">
                        <div className="overview-card-top">
                          <small>Active condition</small>
                          <AlertTriangle size={18} strokeWidth={1.9} className="overview-icon-warning" />
                        </div>
                        <strong>{conditions[0]?.display_name ?? 'No records'}</strong>
                        <p>{conditions[0]?.verification_status ?? 'Not available'}</p>
                      </div>

                      <div className="overview-card">
                        <div className="overview-card-top">
                          <small>Latest observation</small>
                          <CheckCircle2 size={18} strokeWidth={1.9} className="overview-icon-success" />
                        </div>
                        <strong>
                          {observations[0]?.value_text ?? observations[0]?.value_numeric ?? 'No records'}
                          {observations[0]?.unit ? ` ${observations[0].unit}` : ''}
                        </strong>
                        <p>{observations[0]?.test_name ?? 'No recorded test'}</p>
                      </div>
                    </div>

                    <div className="source-panel">
                      <div className="source-panel-left">
                        <span className="source-icon-box">
                          <FileText size={18} strokeWidth={1.85} />
                        </span>
                        <div>
                          <strong>Synthetic structured clinical record</strong>
                          <small>
                            Appointment: {selectedAppointment?.status?.replace('_', ' ') ?? 'none'} · Encounter: {selectedEncounter?.status ?? 'none'}
                          </small>
                        </div>
                      </div>
                      <span className="source-status">Verified locally</span>
                    </div>
                  </div>
                )}

                {/* --- Tab 2: Briefing --- */}
                {activeTab === 'Briefing' && (
                  <div className="tab-content">
                    <div className="content-heading">
                      <div>
                        <span className="content-kicker">Longitudinal History</span>
                        <h3>Source-linked review</h3>
                      </div>
                      <span className="status-label">Read-only history</span>
                    </div>

                    <div className="briefing-list">
                      {allergies.map((item) => (
                        <div className="briefing-row" key={item.id}>
                          <span className="briefing-type is-allergy">Allergy</span>
                          <span className="briefing-detail">
                            <strong>{item.substance}</strong> — {item.reaction ?? 'reaction not recorded'} · {item.verification_status}
                          </span>
                        </div>
                      ))}
                      {conditions.map((item) => (
                        <div className="briefing-row" key={item.id}>
                          <span className="briefing-type">Condition</span>
                          <span className="briefing-detail">
                            <strong>{item.display_name}</strong> · {item.status} · {item.verification_status}
                          </span>
                        </div>
                      ))}
                      {observations.map((item) => (
                        <div className="briefing-row" key={item.id}>
                          <span className="briefing-type">Observation</span>
                          <span className="briefing-detail">
                            <strong>{item.test_name ?? 'Observation'}</strong>: {item.value_text ?? item.value_numeric ?? 'no value'} {item.unit ?? ''}
                          </span>
                        </div>
                      ))}
                      {medications.map((item) => (
                        <div className="briefing-row" key={item.id}>
                          <span className="briefing-type">Medication</span>
                          <span className="briefing-detail">
                            <strong>{item.medicine_name}</strong> · {item.dose ?? 'dose not specified'} · {item.status}
                          </span>
                        </div>
                      ))}
                      {allergies.length + conditions.length + observations.length + medications.length === 0 && (
                        <div className="empty-state">No clinical records are linked to this synthetic patient.</div>
                      )}
                    </div>

                    <p className="clinical-safety">
                      AI-generated drafts require human review. MediFlow AI never independently diagnoses, prescribes, approves, or signs clinical records.
                    </p>
                  </div>
                )}

                {/* --- Tab 3: Feature 1 — Unified Consultation Input + Live Click-to-Edit Hospital A4 Sheet --- */}
                {activeTab === 'Prescription A4' && (
                  <div className="tab-content">
                    <div className="content-heading no-print">
                      <div>
                        <span className="content-kicker">Feature 1 · Clinical Document</span>
                        <h3>Prescription A4 Draft</h3>
                      </div>
                      <span
                        className={`status-label ${
                          prescriptionStatus === 'signed'
                            ? 'is-approved'
                            : prescriptionStatus === 'none'
                              ? 'is-warning'
                              : ''
                        }`}
                      >
                        {clinicalNoteStatusLabel} · {prescriptionStatusLabel}
                      </span>
                    </div>

                    {/* Compact Voice / Written Input Bar Directly Above the Hospital A4 Sheet */}
                    <section className="capture-bar no-print" aria-label="Consultation input">
                      <div className="capture-bar-top">
                        <div className="mode-switch" role="group" aria-label="Consultation input mode">
                          <button
                            type="button"
                            className={consultInputMode === 'voice' ? 'mode-btn active' : 'mode-btn'}
                            onClick={() => setConsultInputMode('voice')}
                          >
                            <Mic size={15} strokeWidth={2} />
                            <span>Voice input</span>
                          </button>
                          <button
                            type="button"
                            className={consultInputMode === 'written' ? 'mode-btn active' : 'mode-btn'}
                            onClick={() => setConsultInputMode('written')}
                          >
                            <Keyboard size={15} strokeWidth={2} />
                            <span>Written input</span>
                          </button>
                        </div>

                        {consultInputMode === 'voice' ? (
                          <div className="capture-voice-inline">
                            <button
                              type="button"
                              className={
                                recordingTarget === 'consult'
                                  ? 'secondary-button recording'
                                  : 'secondary-button'
                              }
                              onClick={
                                recordingTarget === 'consult'
                                  ? stopVoiceCapture
                                  : () => void startVoiceCapture('consult')
                              }
                            >
                              {recordingTarget === 'consult' ? (
                                <Square size={14} strokeWidth={2.2} />
                              ) : (
                                <Mic size={15} strokeWidth={2} />
                              )}
                              <span>
                                {recordingTarget === 'consult' ? 'Stop recording' : 'Start voice capture'}
                              </span>
                            </button>
                            <span className="capture-hint">
                              {recordingTarget === 'consult'
                                ? 'Listening & transcribing… Speaker diarization is not claimed.'
                                : 'Records local audio preview · Transcript stays editable'}
                            </span>
                          </div>
                        ) : (
                          <span className="capture-hint">
                            Type or paste full consultation notes and medicine plan to auto-fill the Hospital A4 sheet
                          </span>
                        )}
                      </div>

                      <textarea
                        className="capture-textarea"
                        value={liveTranscript}
                        onChange={(event) => {
                          setLiveTranscript(event.target.value)
                          if (clinicalNoteStatus !== 'none') {
                            setClinicalNoteStatus('none')
                            setClinicalDraftId('')
                          }
                        }}
                        placeholder={
                          consultInputMode === 'voice'
                            ? 'Click “Start voice capture” to speak, or edit the captured consultation transcript here…'
                            : 'Type or paste the full consultation conversation, symptoms, exam findings, medicines, dosage, frequency, and duration…'
                        }
                      />

                      {consultAudioUrl && (
                        <div className="audio-preview-box">
                          <audio className="audio-preview" controls src={consultAudioUrl}>
                            Local browser audio preview
                          </audio>
                          <small>Local browser audio preview only · Speaker diarization is not claimed.</small>
                        </div>
                      )}

                      <div className="capture-bar-footer">
                        <span className="capture-subnote">
                          AI extracts clinical details and medicines onto the A4 sheet below. Click directly on any A4 field to edit.
                        </span>
                        <div className="capture-bar-actions">
                          <button
                            type="button"
                            className="secondary-button"
                            onClick={() => {
                              if (recordingTarget === 'consult') stopVoiceCapture()
                              clearConsultationState()
                              notify('Hospital A4 sheet reset.')
                            }}
                          >
                            <RotateCcw size={15} strokeWidth={1.9} />
                            <span>Reset</span>
                          </button>
                          <button
                            type="button"
                            className="primary-button"
                            onClick={analyzeAndFillA4}
                            disabled={draftLoading}
                          >
                            <FilePenLine size={15} strokeWidth={2} />
                            <span>{draftLoading ? 'Analyzing & filling A4…' : 'Analyze & Auto-Fill A4'}</span>
                          </button>
                        </div>
                      </div>
                    </section>

                    {aiDraft && (
                      <div className="ai-draft-status no-print">
                        <FilePenLine size={16} strokeWidth={2} />
                        <span>
                          Hospital A4 sheet auto-filled from consultation · Click directly on any line below to edit or remove unwanted details.
                        </span>
                      </div>
                    )}

                    {/* A4 Sheet Toolbar */}
                    <div className="prescription-actions no-print">
                      <div className="prescription-actions-left">
                        <button
                          className="primary-button"
                          type="button"
                          onClick={() => printDocument('a4')}
                        >
                          <Printer size={15} strokeWidth={2} />
                          <span>Print / Export A4 Sheet</span>
                        </button>
                        <button className="secondary-button" type="button" onClick={addMedicineRow}>
                          <Plus size={15} strokeWidth={2} />
                          <span>Add medicine</span>
                        </button>
                        <label className="attach-checkbox">
                          <input
                            type="checkbox"
                            checked={includePersonalNotesOnA4}
                            onChange={(event) => setIncludePersonalNotesOnA4(event.target.checked)}
                          />
                          <span>Include Personal Notes on A4</span>
                        </label>
                      </div>
                      <span className="prescription-actions-note">
                        Direct on-sheet editing · Missing values remain explicit
                      </span>
                    </div>

                    {prescriptionSafetyWarnings.length > 0 && (
                      <div className="warning-panel no-print">
                        <strong>
                          <ShieldAlert size={16} strokeWidth={2} />
                          Deterministic safety review warnings
                        </strong>
                        {prescriptionSafetyWarnings.map((warning) => (
                          <p key={warning}>• {warning}</p>
                        ))}
                      </div>
                    )}

                    {/* Live Click-to-Edit Hospital A4 Prescription & Clinical Sheet */}
                    <div
                      className="print-template print-target-a4"
                      aria-label="Directly editable Hospital A4 clinical and prescription sheet"
                    >
                      <div className="print-template-header">
                        <div className="print-hospital-mark">M</div>
                        <div>
                          <strong className="print-hospital-title">MediFlow Synthetic Hospital</strong>
                          <span className="print-hospital-sub">
                            Hospital A4 Prescription & Clinical Sheet · Academic Demonstration · Not for real clinical use
                          </span>
                        </div>
                        <div className="print-template-date">
                          <span>Date</span>
                          <strong>{printDate}</strong>
                        </div>
                      </div>

                      <div className="print-patient-row">
                        <div>
                          <span>Patient name</span>
                          <strong>{selectedPatient.given_name} {selectedPatient.family_name}</strong>
                        </div>
                        <div>
                          <span>Age / Sex</span>
                          <strong>
                            {ageFrom(selectedPatient.date_of_birth)} yrs / {selectedPatient.sex_at_birth ?? 'Not recorded'}
                          </strong>
                        </div>
                        <div>
                          <span>Synthetic MRN</span>
                          <strong className="meta-mono">{selectedPatient.synthetic_mrn}</strong>
                        </div>
                      </div>

                      <div className="print-section">
                        <h4>Chief complaint</h4>
                        <input
                          className="sheet-inline-input no-print"
                          value={clinicalTemplate.chiefComplaint}
                          placeholder="Click to enter or edit chief complaint…"
                          onChange={(event) => updateClinicalField('chiefComplaint', event.target.value)}
                        />
                        <p className="print-only-text">
                          {clinicalTemplate.chiefComplaint.trim() || 'Pending clinician review'}
                        </p>
                      </div>

                      <div className="print-grid">
                        <div className="print-section">
                          <h4>History of present illness</h4>
                          <textarea
                            className="sheet-inline-textarea no-print"
                            value={clinicalTemplate.history}
                            placeholder="Click to enter or edit history…"
                            onChange={(event) => updateClinicalField('history', event.target.value)}
                          />
                          <p className="print-only-text preserve-lines">
                            {clinicalTemplate.history.trim() || 'Not entered'}
                          </p>
                        </div>

                        <div className="print-section">
                          <h4>Patient-reported facts</h4>
                          <textarea
                            className="sheet-inline-textarea no-print"
                            value={clinicalTemplate.patientFacts}
                            placeholder="Click to enter or edit patient statements…"
                            onChange={(event) => updateClinicalField('patientFacts', event.target.value)}
                          />
                          <p className="print-only-text preserve-lines">
                            {clinicalTemplate.patientFacts.trim() || 'Not entered'}
                          </p>
                        </div>

                        <div className="print-section">
                          <h4>Examination findings</h4>
                          <textarea
                            className="sheet-inline-textarea no-print"
                            value={clinicalTemplate.examination}
                            placeholder="Click to enter or edit examination findings…"
                            onChange={(event) => updateClinicalField('examination', event.target.value)}
                          />
                          <p className="print-only-text preserve-lines">
                            {clinicalTemplate.examination.trim() || 'Not entered'}
                          </p>
                        </div>

                        <div className="print-section">
                          <h4>Assessment (editable draft)</h4>
                          <textarea
                            className="sheet-inline-textarea no-print"
                            value={clinicalTemplate.assessment}
                            placeholder="Draft only — clinician approval required"
                            onChange={(event) => updateClinicalField('assessment', event.target.value)}
                          />
                          <p className="print-only-text preserve-lines">
                            {clinicalTemplate.assessment.trim() || 'Draft only — clinician approval required'}
                          </p>
                        </div>

                        <div className="print-section">
                          <h4>Plan</h4>
                          <textarea
                            className="sheet-inline-textarea no-print"
                            value={clinicalTemplate.plan}
                            placeholder="Click to enter or edit clinical plan…"
                            onChange={(event) => updateClinicalField('plan', event.target.value)}
                          />
                          <p className="print-only-text preserve-lines">
                            {clinicalTemplate.plan.trim() || 'To be decided by clinician.'}
                          </p>
                        </div>

                        <div className="print-section">
                          <h4>Doctor questions / Missing info</h4>
                          <textarea
                            className="sheet-inline-textarea no-print"
                            value={clinicalTemplate.missingInformation}
                            placeholder="Missing information or clinical uncertainty…"
                            onChange={(event) => updateClinicalField('missingInformation', event.target.value)}
                          />
                          <p className="print-only-text preserve-lines">
                            {clinicalTemplate.missingInformation.trim() || 'None recorded'}
                          </p>
                        </div>
                      </div>

                      {/* Medicines Block Directly Editable on Hospital A4 Sheet */}
                      <div className="print-section prescription-medicines">
                        <div className="sheet-section-header">
                          <h4>Rx · Prescription Medicines (click any field to edit)</h4>
                        </div>
                        {prescriptionDraftEdits.length > 0 ? (
                          prescriptionDraftEdits.map((medicine, index) => {
                            const missingFields = getMissingMedicineFields(medicine)
                            return (
                              <div className="prescription-line" key={`med-${index}`}>
                                <div className="screen-only-medicine">
                                  <div className="medicine-line-header">
                                    <span className="medicine-index">{index + 1}.</span>
                                    <input
                                      className="medicine-name-input"
                                      value={medicine.medicine_name}
                                      placeholder="Medicine name (required)"
                                      onChange={(event) =>
                                        updateMedicineField(index, 'medicine_name', event.target.value)
                                      }
                                    />
                                    <button
                                      type="button"
                                      className="remove-medicine-button"
                                      onClick={() => removeMedicineRow(index)}
                                    >
                                      <Trash2 size={14} strokeWidth={1.9} />
                                      <span>Remove</span>
                                    </button>
                                  </div>
                                  <div className="medicine-edit-grid">
                                    <label>
                                      Strength
                                      <input
                                        value={medicine.strength ?? ''}
                                        placeholder="Not specified"
                                        onChange={(event) =>
                                          updateMedicineField(index, 'strength', event.target.value)
                                        }
                                      />
                                    </label>
                                    <label>
                                      Dose
                                      <input
                                        value={medicine.dose ?? ''}
                                        placeholder="Not specified"
                                        onChange={(event) =>
                                          updateMedicineField(index, 'dose', event.target.value)
                                        }
                                      />
                                    </label>
                                    <label>
                                      Route
                                      <input
                                        value={medicine.route ?? ''}
                                        placeholder="Not specified"
                                        onChange={(event) =>
                                          updateMedicineField(index, 'route', event.target.value)
                                        }
                                      />
                                    </label>
                                    <label>
                                      Frequency (times/day)
                                      <input
                                        value={medicine.frequency ?? ''}
                                        placeholder="Not specified"
                                        onChange={(event) =>
                                          updateMedicineField(index, 'frequency', event.target.value)
                                        }
                                      />
                                    </label>
                                    <label>
                                      Duration (days)
                                      <input
                                        value={medicine.duration ?? ''}
                                        placeholder="Not specified"
                                        onChange={(event) =>
                                          updateMedicineField(index, 'duration', event.target.value)
                                        }
                                      />
                                    </label>
                                    <label>
                                      Quantity
                                      <input
                                        value={medicine.quantity ?? ''}
                                        placeholder="Not specified"
                                        onChange={(event) =>
                                          updateMedicineField(index, 'quantity', event.target.value)
                                        }
                                      />
                                    </label>
                                  </div>
                                  <label className="medicine-instructions">
                                    Instructions
                                    <input
                                      value={medicine.instructions ?? ''}
                                      placeholder="e.g., After meals, with water…"
                                      onChange={(event) =>
                                        updateMedicineField(index, 'instructions', event.target.value)
                                      }
                                    />
                                  </label>
                                  {missingFields.length > 0 && (
                                    <div className="missing-fields-note">
                                      Explicitly missing: {missingFields.join(', ')}
                                    </div>
                                  )}
                                  {medicine.source_uncertainty && (
                                    <div className="missing-fields-note">
                                      Source uncertainty: {medicine.source_uncertainty}
                                    </div>
                                  )}
                                </div>

                                <div className="print-only-medicine">
                                  <strong>
                                    {index + 1}. {medicine.medicine_name.trim() || 'Medicine name not specified'}
                                  </strong>
                                  <p>
                                    Strength: {medicine.strength?.trim() || 'Not specified'} · Dose:{' '}
                                    {medicine.dose?.trim() || 'Not specified'} · Route:{' '}
                                    {medicine.route?.trim() || 'Not specified'} · Frequency:{' '}
                                    {medicine.frequency?.trim() || 'Not specified'} · Duration:{' '}
                                    {medicine.duration?.trim() || 'Not specified'} · Quantity:{' '}
                                    {medicine.quantity?.trim() || 'Not specified'}
                                  </p>
                                  {medicine.instructions?.trim() && (
                                    <p>Instructions: {medicine.instructions.trim()}</p>
                                  )}
                                </div>
                              </div>
                            )
                          })
                        ) : (
                          <div className="prescription-line empty-medicine-note">
                            No medicines on sheet yet. Use Voice or Written input above and click “Analyze & Auto-Fill A4”, or click “Add medicine” to enter manually.
                          </div>
                        )}
                      </div>

                      <div className="print-grid">
                        <div className="print-section">
                          <h4>Advice</h4>
                          <textarea
                            className="sheet-inline-textarea no-print"
                            value={adviceText}
                            onChange={(event) => setAdviceText(event.target.value)}
                            placeholder="Click to enter patient advice (one point per line)…"
                          />
                          <p className="print-only-text preserve-lines">
                            {formattedAdvice.length > 0 ? formattedAdvice.join('\n') : 'No advice entered.'}
                          </p>
                        </div>
                        <div className="print-section">
                          <h4>Follow-up</h4>
                          <textarea
                            className="sheet-inline-textarea no-print"
                            value={followUpText}
                            onChange={(event) => setFollowUpText(event.target.value)}
                            placeholder="Click to enter follow-up schedule…"
                          />
                          <p className="print-only-text preserve-lines">
                            {followUpText.trim() || 'To be decided by clinician.'}
                          </p>
                        </div>
                      </div>

                      {/* Optional Embedded Personal Patient Notes (Feature 2) */}
                      {includePersonalNotesOnA4 && activePersonalPoints.length > 0 && (
                        <div className="print-section attached-personal-notes">
                          <h4>
                            {personalTitle.trim() || 'Patient Care Instructions'} (Personal Notes ·{' '}
                            {personalStatusLabel})
                          </h4>
                          <ul className="attached-points-list">
                            {activePersonalPoints.map((point, index) => (
                              <li key={`attached-pt-${index}`}>{point}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {prescriptionSafetyWarnings.length > 0 && (
                        <div className="print-section print-warning">
                          <h4>Deterministic clinical safety warnings</h4>
                          <p>{prescriptionSafetyWarnings.join(' · ')}</p>
                        </div>
                      )}

                      {(aiDraft?.prescription_draft?.missing_prescription_information?.length ?? 0) > 0 && (
                        <div className="print-section print-warning">
                          <h4>Missing prescription information flagged during extraction</h4>
                          <p>{aiDraft?.prescription_draft?.missing_prescription_information?.join(' · ')}</p>
                        </div>
                      )}

                      {liveTranscript.trim() && (
                        <div className="print-section">
                          <h4>Consultation transcript record</h4>
                          <p className="preserve-lines">{liveTranscript.trim()}</p>
                        </div>
                      )}

                      <div className="print-signature-row">
                        <div>
                          <span>Prescriber / Clinician</span>
                          <strong>Dr. {session.displayName.replace(/^Dr\.\s*/i, '')}</strong>
                          <small className="signature-meta">Clinical record: {clinicalNoteStatusLabel}</small>
                        </div>
                        <div>
                          <span>Synthetic signature state</span>
                          <strong className={prescriptionStatus === 'signed' ? 'meta-mono' : ''}>
                            {prescriptionStatus === 'signed'
                              ? `${signedPrescriptionRef || 'ACADEMIC-SYNTHETIC-SIGNATURE'} (${formatDateTime(signedAt)})`
                              : prescriptionStatus === 'approved'
                                ? 'Approved draft · Pending local synthetic signature'
                                : prescriptionStatus === 'created'
                                  ? 'Draft created · Pending clinician approval'
                                  : 'Not signed · Clinician approval required'}
                          </strong>
                          <small className="signature-meta">
                            Local synthetic signature only — must not be interpreted as a real prescription.
                          </small>
                        </div>
                      </div>

                      <div className="print-disclaimer">
                        Draft only · Synthetic academic data · Must not be interpreted as a real prescription · Human clinician approval required · AI never independently diagnoses, prescribes, approves, or signs
                      </div>
                    </div>

                    {/* Clinician Review, Approval & Synthetic Signing Bar */}
                    <div className="governance-bar no-print">
                      <div className="governance-group">
                        <span className="governance-label">Clinical record</span>
                        <div className="governance-buttons">
                          <button
                            className="secondary-button"
                            type="button"
                            onClick={saveClinicalDraft}
                            disabled={!selectedEncounter}
                          >
                            <span>Save clinical draft</span>
                          </button>
                          <button
                            className="secondary-button"
                            type="button"
                            onClick={approveClinicalDraft}
                            disabled={!clinicalDraftId || clinicalNoteStatus !== 'saved'}
                          >
                            <CheckCircle2 size={15} strokeWidth={2} />
                            <span>Approve clinical note</span>
                          </button>
                        </div>
                      </div>

                      <div className="governance-group">
                        <span className="governance-label">Prescription authorization</span>
                        <div className="governance-buttons">
                          <button
                            className="secondary-button"
                            type="button"
                            onClick={createPrescriptionDraft}
                            disabled={!selectedEncounter}
                          >
                            <span>1. Create draft</span>
                          </button>
                          <button
                            className="secondary-button"
                            type="button"
                            onClick={approvePrescriptionDraft}
                            disabled={prescriptionStatus !== 'created'}
                          >
                            <span>2. Approve draft</span>
                          </button>
                          <button
                            className="primary-button"
                            type="button"
                            onClick={signPrescriptionDraft}
                            disabled={prescriptionStatus !== 'approved'}
                          >
                            <CheckCircle2 size={15} strokeWidth={2} />
                            <span>3. Add synthetic signature</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* --- Tab 4: Feature 2 — Personal Patient Notes (Voice/Written + Adaptive Point-Wise AI) --- */}
                {activeTab === 'Personal Notes' && (
                  <div className="tab-content">
                    <div className="content-heading no-print">
                      <div>
                        <span className="content-kicker">Feature 2 · Patient Instructions</span>
                        <h3>Personal Patient Notes</h3>
                      </div>
                      <span
                        className={`status-label ${
                          personalNoteStatus === 'approved' ? 'is-approved' : ''
                        }`}
                      >
                        {personalStatusLabel}
                      </span>
                    </div>

                    {/* Compact Voice / Written Input Bar for Personal Notes */}
                    <section className="capture-bar no-print" aria-label="Personal notes input">
                      <div className="capture-bar-top">
                        <div className="mode-switch" role="group" aria-label="Personal notes input mode">
                          <button
                            type="button"
                            className={personalInputMode === 'voice' ? 'mode-btn active' : 'mode-btn'}
                            onClick={() => setPersonalInputMode('voice')}
                          >
                            <Mic size={15} strokeWidth={2} />
                            <span>Voice input</span>
                          </button>
                          <button
                            type="button"
                            className={personalInputMode === 'written' ? 'mode-btn active' : 'mode-btn'}
                            onClick={() => setPersonalInputMode('written')}
                          >
                            <Keyboard size={15} strokeWidth={2} />
                            <span>Written input</span>
                          </button>
                        </div>

                        {personalInputMode === 'voice' ? (
                          <div className="capture-voice-inline">
                            <button
                              type="button"
                              className={
                                recordingTarget === 'personal'
                                  ? 'secondary-button recording'
                                  : 'secondary-button'
                              }
                              onClick={
                                recordingTarget === 'personal'
                                  ? stopVoiceCapture
                                  : () => void startVoiceCapture('personal')
                              }
                            >
                              {recordingTarget === 'personal' ? (
                                <Square size={14} strokeWidth={2.2} />
                              ) : (
                                <Mic size={15} strokeWidth={2} />
                              )}
                              <span>
                                {recordingTarget === 'personal' ? 'Stop recording' : 'Start voice capture'}
                              </span>
                            </button>
                            <span className="capture-hint">
                              {recordingTarget === 'personal'
                                ? 'Recording personal patient instructions… Speaker diarization is not claimed.'
                                : 'Speak quick instructions or a full explanation — AI formats it point-wise'}
                            </span>
                          </div>
                        ) : (
                          <span className="capture-hint">
                            Short note → AI fixes spelling & formats point-wise · Long conversation → AI extracts main points
                          </span>
                        )}
                      </div>

                      <textarea
                        className="capture-textarea"
                        value={personalRawText}
                        onChange={(event) => setPersonalRawText(event.target.value)}
                        placeholder={
                          personalInputMode === 'voice'
                            ? 'Click “Start voice capture” to dictate patient instructions, or type/edit here…'
                            : 'Type brief instructions (AI fixes spelling & makes clean points) or paste a long conversation (AI summarizes key takeaways)…'
                        }
                      />

                      {personalAudioUrl && (
                        <div className="audio-preview-box">
                          <audio className="audio-preview" controls src={personalAudioUrl}>
                            Local browser audio preview
                          </audio>
                          <small>Local browser audio preview only · Speaker diarization is not claimed.</small>
                        </div>
                      )}

                      <div className="capture-bar-footer">
                        <span className="capture-subnote">
                          Short text is spelling-corrected into points; long conversations are distilled to key patient takeaways.
                        </span>
                        <div className="capture-bar-actions">
                          <button
                            type="button"
                            className="secondary-button"
                            onClick={() => {
                              if (recordingTarget === 'personal') stopVoiceCapture()
                              clearPersonalNotesState()
                              notify('Personal patient notes reset.')
                            }}
                          >
                            <RotateCcw size={15} strokeWidth={1.9} />
                            <span>Reset</span>
                          </button>
                          <button
                            type="button"
                            className="primary-button"
                            onClick={formatPersonalNotesWithAI}
                            disabled={personalLoading}
                          >
                            <ListChecks size={15} strokeWidth={2} />
                            <span>{personalLoading ? 'Formatting into points…' : 'Format into Points'}</span>
                          </button>
                        </div>
                      </div>
                    </section>

                    {/* Personal Notes Toolbar */}
                    <div className="prescription-actions no-print">
                      <div className="prescription-actions-left">
                        <button
                          className="primary-button"
                          type="button"
                          onClick={() => printDocument('personal-notes')}
                        >
                          <Printer size={15} strokeWidth={2} />
                          <span>Print Personal Notes</span>
                        </button>
                        <button className="secondary-button" type="button" onClick={addPersonalPoint}>
                          <Plus size={15} strokeWidth={2} />
                          <span>Add point</span>
                        </button>
                        <label className="attach-checkbox">
                          <input
                            type="checkbox"
                            checked={includePersonalNotesOnA4}
                            onChange={(event) => setIncludePersonalNotesOnA4(event.target.checked)}
                          />
                          <span>Also include on Prescription A4</span>
                        </label>
                      </div>
                      <span className="prescription-actions-note">{personalModeLabel}</span>
                    </div>

                    {/* Directly Editable Point-Wise Personal Patient Notes Sheet */}
                    <div
                      className="print-template print-target-personal"
                      aria-label="Editable Personal Patient Notes instruction sheet"
                    >
                      <div className="print-template-header">
                        <div className="print-hospital-mark">M</div>
                        <div>
                          <strong className="print-hospital-title">MediFlow Synthetic Hospital</strong>
                          <span className="print-hospital-sub">
                            Personal Patient Notes · Care Instructions · Academic Demonstration
                          </span>
                        </div>
                        <div className="print-template-date">
                          <span>Date</span>
                          <strong>{printDate}</strong>
                        </div>
                      </div>

                      <div className="print-patient-row">
                        <div>
                          <span>Patient name</span>
                          <strong>{selectedPatient.given_name} {selectedPatient.family_name}</strong>
                        </div>
                        <div>
                          <span>Age / Sex</span>
                          <strong>
                            {ageFrom(selectedPatient.date_of_birth)} yrs / {selectedPatient.sex_at_birth ?? 'Not recorded'}
                          </strong>
                        </div>
                        <div>
                          <span>Synthetic MRN</span>
                          <strong className="meta-mono">{selectedPatient.synthetic_mrn}</strong>
                        </div>
                      </div>

                      <div className="print-section">
                        <h4>Instruction heading</h4>
                        <input
                          className="sheet-inline-input no-print"
                          value={personalTitle}
                          placeholder="Patient Care Instructions"
                          onChange={(event) => {
                            setPersonalTitle(event.target.value)
                            markPersonalNotesEdited()
                          }}
                        />
                        <p className="print-only-text">
                          <strong>{personalTitle.trim() || 'Patient Care Instructions'}</strong>
                        </p>
                      </div>

                      <div className="print-section personal-points-section">
                        <h4>Key points for patient (click any point to edit)</h4>
                        {personalPoints.length > 0 ? (
                          <div className="personal-points-list">
                            {personalPoints.map((point, index) => (
                              <div className="personal-point-row" key={`pt-${index}`}>
                                <span className="personal-point-num">{index + 1}.</span>
                                <textarea
                                  className="personal-point-input no-print"
                                  rows={2}
                                  value={point}
                                  placeholder="Enter clear instruction point for patient…"
                                  onChange={(event) => updatePersonalPoint(index, event.target.value)}
                                />
                                <p className="print-only-text personal-point-print">
                                  {point.trim() || '—'}
                                </p>
                                <button
                                  type="button"
                                  className="remove-point-btn no-print"
                                  aria-label={`Remove point ${index + 1}`}
                                  onClick={() => removePersonalPoint(index)}
                                >
                                  <Trash2 size={14} strokeWidth={1.9} />
                                </button>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="prescription-line empty-medicine-note">
                            No patient points yet. Dictate or type above and click “Format into Points”, or click “Add point” to write directly.
                          </div>
                        )}
                      </div>

                      {personalSpellingNote && (
                        <div className="print-section no-print">
                          <h4>AI formatting summary</h4>
                          <p>{personalSpellingNote}</p>
                        </div>
                      )}

                      {personalUncertainties.length > 0 && (
                        <div className="print-section print-warning">
                          <h4>Items needing clinician clarification</h4>
                          <p>{personalUncertainties.join(' · ')}</p>
                        </div>
                      )}

                      <div className="print-signature-row">
                        <div>
                          <span>Prepared by clinician</span>
                          <strong>Dr. {session.displayName.replace(/^Dr\.\s*/i, '')}</strong>
                        </div>
                        <div>
                          <span>Clinician review status</span>
                          <strong>{personalStatusLabel}</strong>
                          <small className="signature-meta">
                            Editable patient instructions · Reviewed and approved by clinician before sharing.
                          </small>
                        </div>
                      </div>

                      <div className="print-disclaimer">
                        Draft only · Synthetic academic data · Patient instruction summary for clinician-approved sharing · AI never independently diagnoses, prescribes, or approves
                      </div>
                    </div>

                    <div className="editor-actions no-print">
                      <button
                        type="button"
                        className="secondary-button"
                        onClick={savePersonalNotesDraft}
                      >
                        <span>Save personal notes draft</span>
                      </button>
                      <button
                        type="button"
                        className="primary-button"
                        onClick={approvePersonalNotes}
                        disabled={!personalNoteId || personalNoteStatus !== 'saved'}
                      >
                        <CheckCircle2 size={15} strokeWidth={2} />
                        <span>Approve personal notes</span>
                      </button>
                    </div>
                  </div>
                )}
              </section>
            ) : null}
          </div>
        )}
      </section>
    </main>
  )
}

export default App
