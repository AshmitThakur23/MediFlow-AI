export interface Hospital {
  id: string
  name: string
  code: string
  status: string
}

export interface User {
  id: string
  email: string
  display_name: string
  status: string
  password_hash: string
}

export interface HospitalUser {
  id: string
  hospital_id: string
  user_id: string
  role_code: string
  relationship_scope: string
  status: string
  valid_from: string
  valid_until: string | null
}

export interface Patient {
  id: string
  hospital_id: string
  synthetic_mrn: string
  given_name: string
  family_name: string
  date_of_birth: string
  sex_at_birth: string | null
  identity_status: string
  merged_into_patient_id: string | null
}

export interface Appointment {
  id: string
  hospital_id: string
  patient_id: string
  doctor_hospital_user_id: string
  scheduled_at: string
  status: string
}

export interface Encounter {
  id: string
  hospital_id: string
  patient_id: string
  appointment_id: string | null
  doctor_hospital_user_id: string
  started_at: string | null
  ended_at: string | null
  status: string
  created_at: string
}

export interface ProvenanceRecord {
  id: string
  hospital_id: string
  patient_id: string | null
  encounter_id: string | null
  source_type: string
  source_record_id: string | null
  author_hospital_user_id: string | null
  recorded_at: string
  source_at: string | null
  verification_status: string
  uncertainty: string
  confidence: number | null
  notes: string | null
}

export interface Condition {
  id: string
  hospital_id: string
  patient_id: string
  encounter_id: string | null
  provenance_id: string
  code_system: string | null
  code_value: string | null
  display_name: string
  status: string
  verification_status: string
  onset_at: string | null
  superseded_by_condition_id: string | null
  recorded_at: string
}

export interface AllergyIntolerance {
  id: string
  hospital_id: string
  patient_id: string
  encounter_id: string | null
  provenance_id: string
  substance: string
  reaction: string | null
  criticality: string | null
  status: string
  verification_status: string
  reported_at: string | null
  recorded_at: string
}

export interface Observation {
  id: string
  hospital_id: string
  patient_id: string
  encounter_id: string | null
  provenance_id: string
  observation_type: string
  test_name: string | null
  value_text: string | null
  value_numeric: number | null
  unit: string | null
  reference_range: string | null
  reported_at: string | null
  recorded_at: string
}

export interface MedicationStatement {
  id: string
  hospital_id: string
  patient_id: string
  encounter_id: string | null
  provenance_id: string
  medicine_name: string
  catalogue_item_id: string | null
  statement_type: string
  status: string
  dose: string | null
  start_at: string | null
  end_at: string | null
  superseded_by_statement_id: string | null
  verification_status: string
  recorded_at: string
}

export interface MedicineCatalogueItem {
  id: string
  catalogue_name: string
  catalogue_version: string
  generic_name: string
  brand_name: string | null
  active_ingredient: string | null
  manufacturer: string | null
  strength: string | null
  dosage_form: string | null
  route: string | null
  prescribing_information: string | null
  source_name: string
  source_uri: string | null
  source_updated_at: string | null
  status: string
}

export interface PrescriptionDraftLine {
  id: string
  hospital_id: string
  draft_id: string
  catalogue_item_id: string | null
  medicine_name: string
  strength: string | null
  dose: string | null
  route: string | null
  frequency: string | null
  duration: string | null
  quantity: string | null
  instructions: string | null
}

export interface PrescriptionDraft {
  id: string
  hospital_id: string
  patient_id: string
  encounter_id: string
  created_by_hospital_user_id: string
  status: string
  created_at: string
}

export interface PrescriptionLine {
  id: string
  hospital_id: string
  prescription_id: string
  catalogue_item_id: string | null
  medicine_name: string
  strength: string | null
  dose: string | null
  route: string | null
  frequency: string | null
  duration: string | null
  quantity: string | null
  instructions: string | null
}

export interface SignedPrescription {
  id: string
  hospital_id: string
  patient_id: string
  encounter_id: string
  draft_id: string
  prescribing_hospital_user_id: string
  signed_at: string
  status: string
  signature_reference: string | null
}

export interface DispensingRecord {
  id: string
  hospital_id: string
  patient_id: string
  prescription_id: string
  pharmacist_hospital_user_id: string
  status: string
  substitution_allowed: boolean
  substitution_text: string | null
  clarification_text: string | null
  dispensed_at: string | null
}

export interface ClinicalNoteDraft {
  id: string
  hospital_id: string
  patient_id: string
  encounter_id: string
  created_by_hospital_user_id: string
  transcript_text: string
  chief_complaint: string
  history: string
  patient_facts: string
  doctor_questions: string
  examination_findings: string
  assessment: string
  plan: string
  missing_information: string
  status: string
  created_at: string
  updated_at: string
}

export interface MedicalDocument {
  id: string
  hospital_id: string
  patient_id: string
  encounter_id: string | null
  document_type: string
  original_name: string
  mime_type: string
  object_uri: string
  sha256: string | null
  document_date: string | null
  upload_date: string
  issuing_source: string | null
  page_count: number | null
  processing_status: string
  retention_status: string
  uploaded_by_hospital_user_id: string
}

export interface DocumentPage {
  id: string
  hospital_id: string
  document_id: string
  page_number: number
  width: number | null
  height: number | null
  text_source: string | null
}

export interface DocumentRegion {
  id: string
  hospital_id: string
  document_page_id: string
  region_type: string
  x: number | null
  y: number | null
  width: number | null
  height: number | null
  text: string | null
  confidence: number | null
}

export interface DocumentExtraction {
  id: string
  hospital_id: string
  document_id: string
  document_region_id: string | null
  field_name: string
  extracted_value: string | null
  normalized_value: string | null
  unit: string | null
  reference_range: string | null
  extraction_status: string
  confidence: number | null
  reviewed_by_hospital_user_id: string | null
  reviewed_at: string | null
}

export interface DocumentExtractionCorrection {
  id: string
  hospital_id: string
  extraction_id: string
  corrected_by_hospital_user_id: string
  previous_value: string | null
  corrected_value: string
  reason: string
  corrected_at: string
}

export interface AuthorizationContext {
  user: User
  assignment: HospitalUser
  hospitalId: string
  purpose: string
}

export interface PrescriptionMedicineDraft {
  medicine_name: string
  strength: string | null
  dose: string | null
  route: string | null
  frequency: string | null
  duration: string | null
  quantity: string | null
  instructions: string | null
  source_uncertainty: string | null
}

export interface ExtractedDraft {
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
    medicines: PrescriptionMedicineDraft[]
    advice: string[]
    follow_up: string | null
    missing_prescription_information: string[]
  }
}

export interface PersonalNoteDraft {
  id: string
  hospital_id: string
  patient_id: string
  encounter_id: string | null
  created_by_hospital_user_id: string
  raw_input_text: string
  input_mode: 'voice' | 'written'
  format_mode: 'concise_polish' | 'key_points_summary' | 'manual'
  title: string
  bullet_points: string[]
  status: 'draft' | 'approved' | 'cancelled'
  created_at: string
  updated_at: string
}

export interface FormattedPersonalNotes {
  mode_applied: 'concise_polish' | 'key_points_summary'
  title: string
  bullet_points: string[]
  spelling_corrections_note: string | null
  uncertainties: string[]
}

