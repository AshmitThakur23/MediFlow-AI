import { useMemo, useRef, useState } from 'react'
import './App.css'

type Tab = 'Overview' | 'Briefing' | 'Clinical note' | 'Prescription'

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

function ageFrom(date_of_birth: string) {
  const birth = new Date(`${date_of_birth}T00:00:00`)
  if (Number.isNaN(birth.getTime())) return '—'
  const today = new Date()
  let age = today.getFullYear() - birth.getFullYear()
  if (
    today.getMonth() < birth.getMonth() ||
    (today.getMonth() === birth.getMonth() && today.getDate() < birth.getDate())
  ) age -= 1
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

function greetingForTime() {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 17) return 'Good afternoon'
  return 'Good evening'
}

function App() {
  const [session, setSession] = useState<Session | null>(null)
  const [email, setEmail] = useState(DEMO_EMAIL)
  const [password, setPassword] = useState(DEMO_PASSWORD)
  const [loginError, setLoginError] = useState('')
  const [loginBusy, setLoginBusy] = useState(false)
  const [toast, setToast] = useState('')
  const [activeTab, setActiveTab] = useState<Tab>('Prescription')
  const [activeNav, setActiveNav] = useState<'Overview' | 'Queue' | 'Patients' | 'Documents' | 'Prescriptions'>('Queue')
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
  const [clinicalTemplate, setClinicalTemplate] = useState({
    chiefComplaint: 'Pending clinician review',
    history: '',
    patientFacts: '',
    doctorQuestions: '',
    examination: '',
    assessment: 'Draft only — clinician approval required',
    plan: '',
    missingInformation: '',
  })
  const [draftStatus, setDraftStatus] = useState<'none' | 'saved' | 'created' | 'approved' | 'signed'>('none')
  const [draftId, setDraftId] = useState('')
  const [clinicalDraftId, setClinicalDraftId] = useState('')
  const [isListening, setIsListening] = useState(false)
  const [liveTranscript, setLiveTranscript] = useState('')
  const [draftLoading, setDraftLoading] = useState(false)
  const [aiDraft, setAiDraft] = useState<AiDraft | null>(null)
  const [prescriptionDraftEdits, setPrescriptionDraftEdits] = useState<PrescriptionMedicine[]>([])
  const [speechRecognition, setSpeechRecognition] = useState<SpeechRecognitionLike | null>(null)
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null)
  const [recordedAudioUrl, setRecordedAudioUrl] = useState('')
  const [printDate] = useState(() =>
    new Intl.DateTimeFormat('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    }).format(new Date()),
  )
  const queueInterval = useRef<number | null>(null)

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
    window.setTimeout(() => setToast(''), 3000)
  }

  async function login() {
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
      void loadWorkspace(nextSession)
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
      const firstPatient = patientRows[0]
      setSelectedPatientId(firstPatient?.id ?? '')
      if (firstPatient) {
        void loadClinicalRecords(current, firstPatient.id)
        void loadClinicalTemplate(current, firstPatient.id)
      }
    } catch (error) {
      notify(error instanceof Error ? error.message : 'Could not load workspace.')
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
    setDraftStatus(latest.status === 'approved' ? 'approved' : latest.status === 'draft' ? 'saved' : 'none')
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
    setLiveTranscript((currentTranscript) =>
      currentTranscript.trim() ? currentTranscript : latest.transcript_text,
    )
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
    setAppointments((rows) => rows.map((row) => row.id === selectedAppointment.id ? { ...row, status: 'checked_in' } : row))
    notify('Patient appointment marked checked in.')
  }

  function selectPatient(patient: Patient) {
    setSelectedPatientId(patient.id)
    setDraftStatus('none')
    setDraftId('')
    setClinicalDraftId('')
    if (session) void loadClinicalRecords(session, patient.id)
    if (session) void loadClinicalTemplate(session, patient.id)
    setClinicalTemplate({
      chiefComplaint: 'Pending clinician review',
      history: '',
      patientFacts: '',
      doctorQuestions: '',
      examination: '',
      assessment: 'Draft only — clinician approval required',
      plan: '',
      missingInformation: '',
    })
  }

  function selectNavigation(label: 'Overview' | 'Queue' | 'Patients' | 'Documents' | 'Prescriptions') {
    setActiveNav(label)
    if (label === 'Overview') setActiveTab('Overview')
    if (label === 'Queue') setActiveTab('Overview')
    if (label === 'Prescriptions') setActiveTab('Prescription')
    if (label === 'Patients') setSearch('')
  }

  async function createDraft() {
    if (!session || !selectedPatient || !selectedEncounter) {
      notify('A linked encounter is required.')
      return
    }
    const response = await fetch('/api/v1/prescription-drafts', {
      method: 'POST',
      headers: { ...headers(session), 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_id: selectedPatient.id,
        encounter_id: selectedEncounter.id,
        lines: prescriptionDraftEdits.length > 0
          ? prescriptionDraftEdits.map((medicine) => ({
              medicine_name: medicine.medicine_name,
              strength: medicine.strength || null,
              dose: medicine.dose || null,
              route: medicine.route || null,
              frequency: medicine.frequency || null,
              duration: medicine.duration || null,
              quantity: medicine.quantity || null,
              instructions: medicine.instructions || null,
            }))
          : [{ medicine_name: 'Pending clinician entry', dose: null, route: null, frequency: null, duration: null, quantity: null }],
      }),
    })
    if (!response.ok) {
      notify('The prescription draft could not be created.')
      return
    }
    const draft = await response.json()
    setDraftId(draft.id)
    setDraftStatus('created')
    notify('Prescription draft created. Clinician review is required.')
  }

  async function approveDraft() {
    if (!session || !draftId) return
    const response = await fetch(`/api/v1/prescription-drafts/${draftId}/approval`, {
      method: 'PATCH',
      headers: { ...headers(session), 'Content-Type': 'application/json' },
      body: JSON.stringify({ approved: true }),
    })
    if (!response.ok) {
      notify('The draft approval was rejected.')
      return
    }
    setDraftStatus('approved')
    notify('Draft approved in the demonstration.')
  }

  async function signDraft() {
    if (!session || !draftId) return
    const response = await fetch(`/api/v1/prescriptions?draft_id=${draftId}`, {
      method: 'POST',
      headers: { ...headers(session), 'Content-Type': 'application/json' },
      body: JSON.stringify({ signature_reference: 'ACADEMIC-SYNTHETIC-SIGNATURE' }),
    })
    if (!response.ok) {
      notify('Only an approved draft can be signed.')
      return
    }
    setDraftStatus('signed')
    notify('Synthetic prescription signed in the database.')
  }

  function resetClinicalSession() {
    setLiveTranscript('')
    setAiDraft(null)
    setPrescriptionDraftEdits([])
    setClinicalDraftId('')
    setDraftStatus('none')
    setDraftId('')
    setClinicalTemplate({
      chiefComplaint: 'Pending clinician review',
      history: '',
      patientFacts: '',
      doctorQuestions: '',
      examination: '',
      assessment: 'Draft only — clinician approval required',
      plan: '',
      missingInformation: '',
    })
  }

  async function saveClinicalTemplate() {
    if (!session || !selectedPatient || !selectedEncounter) {
      notify('A linked encounter is required.')
      return
    }
    const response = await fetch('/api/v1/clinical-notes/drafts', {
      method: 'POST',
      headers: { ...headers(session), 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_id: selectedPatient.id,
        encounter_id: selectedEncounter.id,
        transcript_text: liveTranscript.trim() || 'No transcript entered or recorded.',
        chief_complaint: clinicalTemplate.chiefComplaint,
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
      notify('Clinical note draft could not be saved.')
      return
    }
    const draft = await response.json()
    setClinicalDraftId(draft.id)
    setDraftStatus('saved')
    notify('Clinical note draft saved to the database.')
  }

  async function approveClinicalTemplate() {
    if (!session || !clinicalDraftId) return
    const response = await fetch(`/api/v1/clinical-notes/drafts/${clinicalDraftId}/approval`, {
      method: 'PATCH',
      headers: { ...headers(session), 'Content-Type': 'application/json' },
      body: JSON.stringify({ approved: true }),
    })
    if (!response.ok) {
      notify('Clinical note approval was rejected.')
      return
    }
    setClinicalDraftId('')
    setDraftStatus('approved')
    notify('Clinical note draft approved in the demonstration.')
  }

  function printPrescriptionDraft() {
    document.body.dataset.printView = 'prescription'
    window.print()
    window.setTimeout(() => delete document.body.dataset.printView, 0)
  }


  async function startConsultationCapture() {
    const browserWindow = window as typeof window & {
      SpeechRecognition?: SpeechRecognitionConstructor
      webkitSpeechRecognition?: SpeechRecognitionConstructor
    }
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
          setRecordedAudioUrl((current) => {
            if (current) URL.revokeObjectURL(current)
            return URL.createObjectURL(blob)
          })
          stream.getTracks().forEach((track) => track.stop())
        }
        recorder.start()
        setMediaRecorder(recorder)
      }
    } catch {
      notify('Microphone permission was not granted.')
    }

    const Recognition = browserWindow.SpeechRecognition ?? browserWindow.webkitSpeechRecognition
    if (!Recognition) {
      notify('Live browser transcription is not supported in this browser.')
      return
    }
    const recognition = new Recognition()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'en-IN'
    recognition.onresult = (event) => {
      let nextTranscript = liveTranscript
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index]
        if (result.isFinal) nextTranscript += `${result[0].transcript.trim()} `
      }
      setLiveTranscript(nextTranscript.trim())
    }
    recognition.onerror = (event) => {
      setIsListening(false)
      notify(`Speech capture error: ${event.error}`)
    }
    recognition.onend = () => setIsListening(false)
    setSpeechRecognition(recognition)
    recognition.start()
    setIsListening(true)
  }

  function stopConsultationCapture() {
    speechRecognition?.stop()
    if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop()
    setMediaRecorder(null)
    setIsListening(false)
  }

  async function generateGeminiDraft() {
    if (!session || !selectedPatient) return
    if (!liveTranscript.trim()) {
      notify('Add or capture consultation transcript text first.')
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
        notify(body.detail ?? 'Gemini draft generation failed.')
        return
      }
      setAiDraft(body.draft)
      const draft = body.draft
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
      setClinicalTemplate({
        chiefComplaint: draft.chief_complaint || 'Pending clinician review',
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
      notify('Gemini returned an editable draft.')
    } catch {
      notify('Gemini draft generation could not be reached.')
    } finally {
      setDraftLoading(false)
    }
  }

  if (!session) {
    return (
      <main className="login-shell">
        <section className="login-art">
          <div className="login-brand"><span className="brand-symbol">M</span><strong>MediFlow <b>AI</b></strong></div>
          <div className="login-hero">
            <span className="eyebrow">ACADEMIC CLINICAL WORKSPACE</span>
            <h1>Connected care.<br /><em>Clear decisions.</em></h1>
            <p>Source-linked patient history and clinician-controlled consultation workflows.</p>
            <div className="login-metrics">
              <div><strong>3</strong><span>Synthetic patients</span></div>
              <div><strong>0</strong><span>AI approvals</span></div>
              <div><strong>100%</strong><span>Human-controlled</span></div>
            </div>
          </div>
        </section>
        <section className="login-panel">
          <div className="login-card">
            <div className="login-status"><span></span> Local synthetic workspace</div>
            <h2>Welcome back</h2>
            <p>Sign in to the MediFlow demonstration.</p>
            <label>Email address<input value={email} onChange={(event) => setEmail(event.target.value)} /></label>
            <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
            {loginError && <div className="login-error">{loginError}</div>}
            <button className="sign-in-button" onClick={login} disabled={loginBusy}>{loginBusy ? 'Signing in…' : 'Enter workspace'} <span>→</span></button>
            <div className="login-safety">Synthetic patient data · No real clinical use</div>
          </div>
        </section>
      </main>
    )
  }

  const filteredPatients = patients.filter((patient) => {
    const query = search.trim().toLowerCase()
    if (!query) return true
    return `${patient.given_name} ${patient.family_name} ${patient.synthetic_mrn}`.toLowerCase().includes(query)
  })

  return (
    <main className="dashboard">
      {toast && <div className="toast">{toast}</div>}
      <aside className="sidebar">
        <div className="brand"><span className="brand-symbol">M</span><strong>MediFlow <b>AI</b></strong></div>
        <nav>
          <button className={activeNav === 'Overview' ? 'nav-link active' : 'nav-link'} onClick={() => selectNavigation('Overview')}><span className="nav-icon">▦</span><span>Overview</span></button>
          <button className={activeNav === 'Queue' ? 'nav-link active' : 'nav-link'} onClick={() => selectNavigation('Queue')}><span className="nav-icon">◫</span><span>Queue</span><b>{patients.length}</b></button>
          <button className={activeNav === 'Prescriptions' ? 'nav-link active' : 'nav-link'} onClick={() => selectNavigation('Prescriptions')}><span className="nav-icon">Rx</span><span>Prescriptions</span></button>
        </nav>
        <div className="sidebar-bottom">
          <div className="doctor-profile">
            <span className="doctor-avatar">{session.displayName.split(' ').map((word) => word[0]).slice(-2).join('')}</span>
            <div><strong>{session.displayName}</strong><small>{session.roleCode}</small></div>
            <button onClick={() => {
              if (queueInterval.current) window.clearInterval(queueInterval.current)
              setSession(null)
            }}>Exit</button>
          </div>
        </div>
      </aside>

      <section className="main">
        <header className="header">
          <div><span className="date-label">LOCAL DEMONSTRATION · SYNTHETIC DATA</span><h1>{greetingForTime()}, Doctor</h1></div>
          <div className="header-actions">
            <label className="search-button"><span>⌕</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search patients" /></label>
            <button className="primary-button" onClick={checkInPatient}>Check in selected patient</button>
          </div>
        </header>

        {loading ? (
          <div className="loading-state">Loading verified local workspace…</div>
        ) : (
          <div className="workspace-grid">
            <section className="queue-card">
              <div className="panel-heading"><div><span>LOCAL QUEUE</span><h2>Waiting patients</h2></div><small>{filteredPatients.length} patients</small></div>
              <div className="queue-table-heading"><span>Patient</span><span>Visit</span><span>Time</span></div>
              <div className="patient-list">
                {filteredPatients.map((patient) => {
                  const appointment = appointments.find((row) => row.patient_id === patient.id)
                  return (
                    <button
                      className={selectedPatient?.id === patient.id ? 'patient-row selected' : 'patient-row'}
                      onClick={() => selectPatient(patient)}
                      key={patient.id}
                    >
                      <span className="patient-avatar">{initials(patient)}</span>
                      <span className="patient-info"><strong>{patient.given_name} {patient.family_name}</strong><small>{ageFrom(patient.date_of_birth)} yrs · {patient.synthetic_mrn}</small></span>
                      <span className="patient-reason"><strong>Clinical follow-up</strong><small>{appointment?.status ?? 'not scheduled'}</small></span>
                      <span className="wait-time">{appointment ? formatTime(appointment.scheduled_at) : '—'}</span>
                    </button>
                  )
                })}
                {filteredPatients.length === 0 && <div className="empty-state">No synthetic patient matches this search.</div>}
              </div>
            </section>

            {selectedPatient ? (
              <section className="patient-card">
                <div className="patient-card-header">
                  <div className="patient-identity">
                    <span className="large-avatar">{initials(selectedPatient)}</span>
                    <div><span>SELECTED PATIENT</span><h2>{selectedPatient.given_name} {selectedPatient.family_name}</h2><small>{ageFrom(selectedPatient.date_of_birth)} yrs · {selectedPatient.sex_at_birth ?? 'not recorded'} · {selectedPatient.synthetic_mrn}</small></div>
                  </div>
                  <div className="identity-actions"><span className="verified">{selectedPatient.identity_status}</span></div>
                </div>
                <div className="tabs">
                  {(['Overview', 'Briefing', 'Clinical note', 'Prescription'] as Tab[]).map((tab) => (
                    <button className={activeTab === tab ? 'active' : ''} onClick={() => setActiveTab(tab)} key={tab}>{tab}</button>
                  ))}
                </div>

                {activeTab === 'Overview' && (
                  <div className="tab-content">
                    <div className="content-heading"><div><span>CURRENT RECORD</span><h3>Patient overview</h3></div><span className="state-chip">Database-backed</span></div>
                    <div className="overview-grid">
                      <div className="overview-card"><span className="card-icon coral">!</span><div><small>Allergies</small><strong>{allergies[0]?.substance ?? 'No records'}</strong><p>{allergies[0]?.reaction ?? 'No recorded reaction'}</p></div></div>
                      <div className="overview-card"><span className="card-icon amber">+</span><div><small>Active condition</small><strong>{conditions[0]?.display_name ?? 'No records'}</strong><p>{conditions[0]?.verification_status ?? 'Not available'}</p></div></div>
                      <div className="overview-card"><span className="card-icon green">✓</span><div><small>Latest observation</small><strong>{observations[0]?.value_text ?? observations[0]?.value_numeric ?? 'No records'}</strong><p>{observations[0]?.test_name ?? 'No recorded test'}</p></div></div>
                    </div>
                    <div className="source-panel"><span className="document-icon">DB</span><div><strong>Synthetic structured record</strong><small>Loaded from the local MediFlow database</small></div><span className="source-status">Verified locally</span></div>
                  </div>
                )}

                {activeTab === 'Briefing' && (
                  <div className="tab-content">
                    <div className="content-heading"><div><span>BRIEFING</span><h3>Source-linked review</h3></div><span className="state-chip">Draft</span></div>
                    <div className="briefing-list">
                      {allergies.map((item) => <div key={item.id}><b>AR</b><span>{item.substance}: {item.reaction ?? 'reaction not recorded'} · {item.verification_status}</span></div>)}
                      {conditions.map((item) => <div key={item.id}><b>CX</b><span>{item.display_name} · {item.status} · {item.verification_status}</span></div>)}
                      {observations.map((item) => <div key={item.id}><b>OB</b><span>{item.test_name ?? 'Observation'}: {item.value_text ?? item.value_numeric ?? 'no value'} {item.unit ?? ''}</span></div>)}
                      {medications.map((item) => <div key={item.id}><b>RX</b><span>{item.medicine_name} · {item.dose ?? 'dose not specified'} · {item.status}</span></div>)}
                      {allergies.length + conditions.length + observations.length + medications.length === 0 && <div className="empty-state">No clinical records are linked to this synthetic patient.</div>}
                    </div>
                    <p className="clinical-safety">AI-generated findings are drafts only. MediFlow does not independently diagnose or approve treatment.</p>
                  </div>
                )}

                {activeTab === 'Clinical note' && (
                  <div className="tab-content">
                    <div className="content-heading"><div><span>CLINICAL DOCUMENTATION</span><h3>Consultation note draft</h3></div><span className="state-chip">{draftStatus === 'approved' ? 'Approved in database' : draftStatus === 'saved' ? 'Saved in database' : 'Not approved'}</span></div>
                    <div className="voice-controls">
                      <button
                        className={isListening ? 'secondary-button recording' : 'secondary-button'}
                        onClick={isListening ? stopConsultationCapture : startConsultationCapture}
                        type="button"
                      >
                        {isListening ? 'Stop recording' : 'Start voice capture'}
                      </button>
                      <span>{isListening ? 'Listening and transcribing…' : 'Browser Web Speech or manual transcript'}</span>
                    </div>
                    <textarea
                      className="transcript-editor"
                      value={liveTranscript}
                      onChange={(event) => setLiveTranscript(event.target.value)}
                      placeholder="Speak in consultation or paste a transcript..."
                    />
                    {recordedAudioUrl && (
                      <audio className="audio-preview" controls src={recordedAudioUrl}>
                        Browser audio preview
                      </audio>
                    )}
                    <div className="clinical-template">
                      <label>Chief complaint<textarea value={clinicalTemplate.chiefComplaint} onChange={(event) => setClinicalTemplate((current) => ({ ...current, chiefComplaint: event.target.value }))} /></label>
                      <label>History of present illness<textarea value={clinicalTemplate.history} onChange={(event) => setClinicalTemplate((current) => ({ ...current, history: event.target.value }))} /></label>
                      <label>Patient-reported facts<textarea value={clinicalTemplate.patientFacts} onChange={(event) => setClinicalTemplate((current) => ({ ...current, patientFacts: event.target.value }))} /></label>
                      <label>Doctor questions<textarea value={clinicalTemplate.doctorQuestions} onChange={(event) => setClinicalTemplate((current) => ({ ...current, doctorQuestions: event.target.value }))} /></label>
                      <label>Examination findings<textarea value={clinicalTemplate.examination} onChange={(event) => setClinicalTemplate((current) => ({ ...current, examination: event.target.value }))} /></label>
                      <label>Assessment<textarea value={clinicalTemplate.assessment} onChange={(event) => setClinicalTemplate((current) => ({ ...current, assessment: event.target.value }))} /></label>
                      <label>Plan<textarea value={clinicalTemplate.plan} onChange={(event) => setClinicalTemplate((current) => ({ ...current, plan: event.target.value }))} /></label>
                      <label>Missing information / uncertainty<textarea value={clinicalTemplate.missingInformation} onChange={(event) => setClinicalTemplate((current) => ({ ...current, missingInformation: event.target.value }))} /></label>
                    </div>
                    <div className="print-clinical-template" aria-label="A4 clinical note draft">
                      <div className="print-template-header">
                        <div className="print-hospital-mark">M</div>
                        <div>
                          <strong>MediFlow Synthetic Hospital</strong>
                          <span>Clinical consultation draft · Not for real clinical use</span>
                        </div>
                        <div className="print-template-date">
                          <span>Date</span>
                          <strong>{printDate}</strong>
                        </div>
                      </div>
                      <div className="print-patient-row">
                        <div><span>Patient name</span><strong>{selectedPatient.given_name} {selectedPatient.family_name}</strong></div>
                        <div><span>Age / Gender</span><strong>{ageFrom(selectedPatient.date_of_birth)} / {selectedPatient.sex_at_birth ?? 'Not recorded'}</strong></div>
                        <div><span>Patient MRN</span><strong>{selectedPatient.synthetic_mrn}</strong></div>
                      </div>
                      <div className="print-clinical-grid">
                        <div><h4>Chief complaint</h4><p>{clinicalTemplate.chiefComplaint || 'Not entered'}</p></div>
                        <div><h4>History of present illness</h4><p>{clinicalTemplate.history || 'Not entered'}</p></div>
                        <div><h4>Patient-reported facts</h4><p>{clinicalTemplate.patientFacts || 'Not entered'}</p></div>
                        <div><h4>Doctor questions</h4><p>{clinicalTemplate.doctorQuestions || 'None recorded'}</p></div>
                        <div><h4>Examination findings</h4><p>{clinicalTemplate.examination || 'Not entered'}</p></div>
                        <div><h4>Assessment</h4><p>{clinicalTemplate.assessment || 'Draft only — clinician approval required'}</p></div>
                        <div><h4>Plan</h4><p>{clinicalTemplate.plan || 'Not entered'}</p></div>
                        <div><h4>Missing information / uncertainty</h4><p>{clinicalTemplate.missingInformation || 'None recorded'}</p></div>
                      </div>
                      <div className="print-clinical-transcript">
                        <h4>Consultation transcript</h4>
                        <p>{liveTranscript.trim() || 'No transcript entered or recorded.'}</p>
                      </div>
                      <div className="print-disclaimer">DRAFT ONLY · Synthetic academic data · Clinician review required · Not a confirmed clinical record</div>
                    </div>
                    {aiDraft && <div className="ai-draft-status">Gemini draft received · Human review required</div>}
                    <div className="editor-actions">
                      <button className="secondary-button" onClick={resetClinicalSession}>New transcript / reset</button>
                      <button className="secondary-button" onClick={() => setDraftStatus('none')}>Reset draft</button>
                      <button className="secondary-button" onClick={generateGeminiDraft} disabled={draftLoading}>{draftLoading ? 'Generating…' : 'Generate Gemini draft'}</button>
                      <button className="secondary-button" onClick={saveClinicalTemplate} disabled={!selectedEncounter}>Save template</button>
                      <button className="primary-button" onClick={approveClinicalTemplate} disabled={!clinicalDraftId}>Approve clinical note</button>
                    </div>
                  </div>
                )}

                {activeTab === 'Prescription' && (
                  <div className="tab-content">
                    <div className="content-heading"><div><span>PRESCRIPTION WORKSPACE</span><h3>Clinician-reviewable draft</h3></div><span className={`state-chip ${draftStatus === 'signed' ? 'signed' : 'warning'}`}>{draftStatus === 'signed' ? 'Signed locally' : 'Not signed'}</span></div>
                    <div className="prescription-actions">
                      <button className="secondary-button" onClick={printPrescriptionDraft}>Print A4 draft</button>
                      <span>Editable · Draft · Clinician approval required</span>
                    </div>
                    <div className="print-template prescription-template" aria-label="A4 prescription draft">
                      <div className="print-template-header">
                        <div className="print-hospital-mark">M</div>
                        <div>
                          <strong>MediFlow Synthetic Hospital</strong>
                          <span>Academic demonstration · Not for real clinical use</span>
                        </div>
                        <div className="print-template-date">
                          <span>Date</span>
                          <strong>{printDate}</strong>
                        </div>
                      </div>
                      <div className="print-patient-row">
                        <div><span>Patient name</span><strong>{selectedPatient.given_name} {selectedPatient.family_name}</strong></div>
                        <div><span>Age / Gender</span><strong>{ageFrom(selectedPatient.date_of_birth)} / {selectedPatient.sex_at_birth ?? 'Not recorded'}</strong></div>
                        <div><span>Patient MRN</span><strong>{selectedPatient.synthetic_mrn}</strong></div>
                      </div>
                      <div className="print-section">
                        <h4>Chief complaint</h4>
                        <p>{aiDraft?.chief_complaint ?? 'Pending Gemini or clinician review'}</p>
                      </div>
                      <div className="print-section">
                        <h4>Consultation transcript</h4>
                        <p>{liveTranscript.trim() || 'No transcript entered or recorded.'}</p>
                      </div>
                      <div className="print-grid">
                        <div className="print-section">
                          <h4>History of present illness</h4>
                          <p>{clinicalTemplate.history || 'Not entered'}</p>
                        </div>
                        <div className="print-section">
                          <h4>Patient-reported facts</h4>
                          <p>{clinicalTemplate.patientFacts || 'Not entered'}</p>
                        </div>
                        <div className="print-section">
                          <h4>Doctor questions</h4>
                          <p>{clinicalTemplate.doctorQuestions || 'None recorded'}</p>
                        </div>
                        <div className="print-section">
                          <h4>Examination findings</h4>
                          <p>{clinicalTemplate.examination || 'Not entered'}</p>
                        </div>
                        <div className="print-section">
                          <h4>Assessment</h4>
                          <p>{clinicalTemplate.assessment || 'Draft only — clinician approval required'}</p>
                        </div>
                        <div className="print-section">
                          <h4>Plan</h4>
                          <p>{clinicalTemplate.plan || 'To be decided by clinician.'}</p>
                        </div>
                      </div>
                      <div className="print-section prescription-medicines">
                        <h4>Prescription / Draft medicines</h4>
                        {prescriptionDraftEdits.length > 0 ? (
                          prescriptionDraftEdits.map((medicine, index) => (
                            <div className="prescription-line prescription-line-editable" key={`${medicine.medicine_name}-${index}`}>
                              <strong>{index + 1}. <input value={medicine.medicine_name} onChange={(event) => setPrescriptionDraftEdits((rows) => rows.map((row, rowIndex) => rowIndex === index ? { ...row, medicine_name: event.target.value } : row))} /></strong>
                              <div className="medicine-edit-grid">
                                <label>Strength<input value={medicine.strength ?? ''} onChange={(event) => setPrescriptionDraftEdits((rows) => rows.map((row, rowIndex) => rowIndex === index ? { ...row, strength: event.target.value } : row))} /></label>
                                <label>Dose<input value={medicine.dose ?? ''} onChange={(event) => setPrescriptionDraftEdits((rows) => rows.map((row, rowIndex) => rowIndex === index ? { ...row, dose: event.target.value } : row))} /></label>
                                <label>Route<input value={medicine.route ?? ''} onChange={(event) => setPrescriptionDraftEdits((rows) => rows.map((row, rowIndex) => rowIndex === index ? { ...row, route: event.target.value } : row))} /></label>
                                <label>Frequency<input value={medicine.frequency ?? ''} onChange={(event) => setPrescriptionDraftEdits((rows) => rows.map((row, rowIndex) => rowIndex === index ? { ...row, frequency: event.target.value } : row))} /></label>
                                <label>Duration<input value={medicine.duration ?? ''} onChange={(event) => setPrescriptionDraftEdits((rows) => rows.map((row, rowIndex) => rowIndex === index ? { ...row, duration: event.target.value } : row))} /></label>
                                <label>Quantity<input value={medicine.quantity ?? ''} onChange={(event) => setPrescriptionDraftEdits((rows) => rows.map((row, rowIndex) => rowIndex === index ? { ...row, quantity: event.target.value } : row))} /></label>
                              </div>
                              <label className="medicine-instructions">Instructions<input value={medicine.instructions ?? ''} onChange={(event) => setPrescriptionDraftEdits((rows) => rows.map((row, rowIndex) => rowIndex === index ? { ...row, instructions: event.target.value } : row))} /></label>
                            </div>
                          ))
                        ) : (
                          <div className="prescription-line">
                            <strong>Pending Gemini / clinician entry</strong>
                            <span>No medicine candidate was generated from this transcript.</span>
                          </div>
                        )}
                      </div>
                      <div className="print-grid">
                        <div className="print-section">
                          <h4>Advice</h4>
                          <p>{aiDraft?.prescription_draft?.advice?.join(' • ') || 'No Gemini advice generated yet.'}</p>
                        </div>
                        <div className="print-section">
                          <h4>Follow-up</h4>
                          <p>{aiDraft?.prescription_draft?.follow_up || 'To be decided by clinician.'}</p>
                        </div>
                      </div>
                      {(aiDraft?.prescription_draft?.missing_prescription_information?.length ?? 0) > 0 && (
                        <div className="print-section print-warning">
                          <h4>Missing prescription information</h4>
                          <p>{aiDraft?.prescription_draft?.missing_prescription_information?.join(' • ')}</p>
                        </div>
                      )}
                      <div className="print-signature-row">
                        <div><span>Prescriber / clinician</span><strong>Dr. {session.displayName.replace('Dr. ', '')}</strong></div>
                        <div><span>Signature</span><strong>{draftStatus === 'signed' ? 'ACADEMIC-SYNTHETIC-SIGNATURE' : 'Pending approval'}</strong></div>
                      </div>
                      <div className="print-disclaimer">DRAFT ONLY · Synthetic academic data · Not a real prescription · Human clinician approval required</div>
                    </div>
                    <div className="editor-actions">
                      <button className="secondary-button" onClick={createDraft} disabled={!selectedEncounter}>Create draft</button>
                      <button className="secondary-button" onClick={approveDraft} disabled={draftStatus !== 'created'}>Approve draft</button>
                      <button className="primary-button" onClick={signDraft} disabled={draftStatus !== 'approved'}>Sign prescription</button>
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
