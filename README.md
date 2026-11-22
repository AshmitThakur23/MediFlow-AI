# MediFlow AI

> **Current status:** The repository contains a documented academic-MVP backend foundation with SQLAlchemy clinical models, SQLite-tested tenant integrity, synthetic local-account authentication, tenant-scoped APIs, provenance and typed clinical-history APIs, prescription workflows, document/source-reference metadata, and a React doctor-workspace showcase. Binary document storage, OCR, queue breadth, AI extraction, audio workflows and production services remain incomplete.

## Permanent Engineering Policy

The following rules govern all current and future work on MediFlow AI:

1. Never depend exclusively on Copilot's conversation history or context window.
2. Repository Markdown documentation is the persistent source of project knowledge.
3. Before every task, inspect `README.md`, `AGENTS.md`, applicable Copilot instructions, `CURRENT_TASK.md`, and relevant architecture documentation.
4. After every completed task, update the appropriate documentation with the actual changes and test results.
5. Record every newly evaluated technology in `TECHNOLOGY_RADAR.md`.
6. Document the rationale for every adopted or rejected architectural technology decision in `TECHNOLOGY_DECISIONS.md`, and create an ADR where appropriate.
7. Maintain dependency versions, licensing information, security considerations, and compatibility.
8. Never claim that a feature or test passed without evidence.
9. Never overwrite historical development records; append dated entries and preserve Git history.
10. If context is lost, reconstruct the current project state from documentation and Git history before proceeding.

MediFlow AI is a proposed AI-assisted clinical workflow platform for healthcare professionals. Its purpose is to connect a patient's available medical history with the current consultation, prepare source-linked decision-support information, document consented consultations, and produce reviewable drafts for clinical notes, prescriptions, and patient-care instructions.

The system is designed to support the doctor. **AI must never independently diagnose, prescribe, sign, approve, or otherwise make a clinical decision.** Every AI-generated summary, extracted fact, warning, medicine suggestion, prescription draft, care instruction, risk label, and proposed question remains a draft until reviewed and authorized by an appropriately qualified healthcare professional.

## 1. Project Overview and Purpose

MediFlow AI brings together:

- A longitudinal, chronological view of a patient's available medical records
- Medical-document extraction and source-linked report review
- Queue-triggered preparation of a concise patient briefing
- Consent-aware clinical audio capture and transcript generation
- Structured, editable consultation documentation
- Verified medicine-catalogue search and prescription drafting
- Patient-specific care instructions and follow-up tracking
- Role-based access, versioning, audit trails, and privacy controls

The proposed system aims to reduce repetitive searching and manual documentation while preserving the original evidence and keeping the clinician in control of assessment and treatment decisions.

## 2. Product Vision and Objectives

The proposed vision is to connect a patient's medical story across three points in time:

- **Historical records:** available prior consultations, conditions, allergies, medicines, reports, admissions, procedures, prescriptions and instructions.
- **Current consultation:** the selected patient, consented conversation, examination information, doctor assessment, care decisions and approved documentation.
- **Future care:** active instructions, follow-up dates, recommended investigations, completed actions and subsequent encounters.

MediFlow AI is intended to make relevant information easier to find and more traceable without hiding the source record or removing clinical control from the doctor. The proposal defines these objectives:

1. Create a unified chronological view of a patient's available medical history.
2. Analyse uploaded medical documents and extract useful information with links to original sources.
3. Prepare a concise patient briefing when the doctor is about to call a patient from the queue.
4. Record a consultation only after required consent and convert speech into a timestamped transcript.
5. Distinguish patient statements, doctor statements, examination findings and verified historical facts.
6. Generate editable consultation notes, prescription drafts and patient-care instructions.
7. Highlight relevant allergies, medication conflicts, abnormal historical results and missing information.
8. Keep the doctor in control of diagnosis, treatment decisions, prescription approval and signing.
9. Protect sensitive records through role-based access, consent controls and audit logs.

These objectives describe the proposed product. They are not confirmation that any objective has been implemented.

## 3. Problem Statement

Patient information is often distributed across consultation notes, prescriptions, laboratory reports, radiology reports, discharge summaries, operation notes, and other documents. During a new visit, a doctor may have to search these sources while listening to the patient and maintaining documentation. Important information can be difficult to locate, and patients may repeat the same information.

Manual preparation of consultation notes, prescriptions, and care instructions can also consume significant time. The proposed problem addressed by MediFlow AI is not merely faster note generation: it is the safer organization of fragmented information, clear provenance, reconciliation of conflicting records, and preservation of human clinical judgment.

## 4. Nine Clinical Modules

The following modules are proposed for the complete product; they do not describe implemented functionality.

### 4.1 Patient Profile and Longitudinal Medical History

- Organize identity, encounters, diagnoses, allergies, medicines, surgeries, admissions, reports, prescriptions, instructions, and follow-up history.
- Preserve date, source, author, and verification status.
- Distinguish confirmed, patient-reported, imported, and AI-generated information.
- Add new facts without silently overwriting approved records.
- Use careful patient-matching controls to prevent record mixing.

## 5. Longitudinal Clinical Memory

The proposed longitudinal patient record is a source-preserving clinical timeline, not a free-form AI memory:

- Every dated record retains its document or encounter date, source, author, upload date where applicable and verification status.
- Confirmed clinician-recorded facts, patient-reported statements, imported records and AI-generated drafts remain visually and structurally distinct.
- Old records are never silently overwritten. A new approved fact is added as a versioned correction or a new timeline entry.
- Duplicate-patient and patient-matching controls must prevent records from different patients or hospitals from being combined.
- Medicines reported by the patient must be reconciled separately from current medication statements and medicines only found in historical prescriptions.
- Conflicting records remain visible until the doctor reviews, confirms or closes the conflict.
- Missing information is unknown and must not be interpreted as a negative finding.
- Relevant treatment outcomes, previous instructions and follow-up status remain available in the chronological history.
- AI summaries and vector-search results are proposed supporting views; structured and source-linked records remain the source of truth.

### 4.2 Medical Document and Report Intelligence

- Accept laboratory reports, radiology reports, prescriptions, discharge summaries, and other supported documents.
- Use OCR and document parsing to extract searchable fields with page, section, or region references where possible.
- Preserve original values, units, report reference ranges, source, and uncertainty.
- Summarize radiologist findings and extracted results without presenting an AI diagnosis from an image.
- Flag potentially abnormal values according to report context and supported rules.
- Refrain from comparison when dates, units, or test methods are insufficiently comparable.

The proposed supported document types include laboratory reports, radiology reports, prescriptions, discharge summaries, operation notes and other approved clinical documents. Document processing should extract text and relevant fields while preserving selectable-text, OCR or manual-entry provenance. Extracted test names, values, units and reference ranges should remain linked to the original report.

For radiology, the system may summarize the written findings and impression but must not independently diagnose from an image. Every finding should retain document identity, document date, upload date, issuing source, processing status, page count and exact page or section reference where supported. Where text or regions can be located, the source viewer should navigate to the relevant page, text, table row or region.

Low-confidence, unclear or ambiguous extraction must request human verification. Document corrections should record the person, date and reason. One-click trend comparison should show each result with date, value, original unit, reference range and source report, normalize units only through a validated process and warn when test methods or ranges differ. The original document must remain available and must not be replaced by an AI summary.

**Medical Document Intelligence / Source References:** When supported by the document-processing pipeline, store page-level references and bounding-box coordinates for extracted text, table rows or regions. These references should enable the doctor to navigate to the relevant location in the original PDF or image and verify the AI extraction.

### 4.3 Queue-Connected AI Patient Briefing

- Prepare authorized patient context in the background when the patient joins the queue.
- Present critical, important, and contextual findings with source, date, reason, and verification status.
- Distinguish current medicines from historical prescriptions and patient-reported use.
- Open original reports and timeline entries directly from briefing findings.
- Continue queue and consultation operations if preparation is incomplete or fails.

The proposed briefing contains relevant previous diagnoses and consultations, verified or unverified allergies and reactions, current medicines separately from historical prescriptions, important laboratory and imaging findings, surgeries, admissions, discharge summaries, previous outcomes and follow-up status. It also presents missing information and a short list of questions the doctor may consider asking.

Findings are presented in proposed clinical-attention levels:

| Level | Meaning |
| --- | --- |
| Critical | A potentially serious, time-sensitive issue identified by a validated, versioned rule or clearly documented source, never by an LLM alone |
| Important | A relevant allergy, medication issue, previous condition, abnormal result or unresolved follow-up |
| Contextual | Background history that may help interpretation but is not currently urgent |

Every important AI finding must show why it appeared, its source, date and verification status and must open the supporting record or exact document. Each proposed level is for clinician attention, not autonomous diagnosis or escalation.

When a patient checks in, authorized records should be prepared in the background. Preparation status must support:

- **Ready:** completed briefing with included sources and preparation time.
- **Partially ready:** completed sections shown while remaining work continues.
- **Processing:** active processing is visible and the doctor can continue.
- **Failed:** failed document or service identified where safe, with retry or manual review and no implied analysis.
- **No records available:** no accessible prior record is found; this must not imply no medical history exists.
- **Stale data:** last update date shown with warning that newer records may be unavailable.

The doctor can mark a finding as reviewed, incorrect, outdated or requiring confirmation, with an audit trail. The one-click call-next experience must open the correct patient and encounter and must not start audio recording.

**AI Patient Briefing / Performance:** For routine consultations with already indexed records and relevant context available, the proposed engineering target is to make the briefing ready in approximately 20–30 seconds. This is an engineering goal, not a guaranteed completion time. Complex cases, large documents, unavailable services or incomplete records may take longer. The system must display processing status and must never fabricate a completed briefing.

### 4.4 Ambient Doctor–Patient Consultation Recording

- Record only after appropriate consent and with pause, stop, and manual-documentation controls.
- Produce a timestamped transcript and probabilistic speaker attribution.
- Allow correction of transcript text and speaker labels.
- Apply configured consent, retention, deletion, and access policies to recordings.

With appropriate consent, audio can be captured through the consultation interface and converted into timestamped transcript segments. Speaker diarization may label turns as Doctor, Patient or Other/Uncertain, but attribution is probabilistic and is not guaranteed identity verification. Where the selected speech service provides confidence, it should be retained for review.

Manual documentation remains available when recording is declined or unavailable. The system should handle overlapping speech, background noise, accents, code-switching and unclear words using uncertainty markers rather than silently guessing. The doctor or authorized staff must be able to correct both text and speaker labels. Corrected and original transcript versions must remain available with author, timestamp and audit history.

### 4.5 AI Clinical Information Extraction and Documentation

- Separate patient statements, doctor questions, doctor findings, and clinician-confirmed facts.
- Detect negation, uncertainty, duration, conflicts, and missing information.
- Preserve speaker, timestamp, source, and uncertainty for extracted facts.
- Generate editable clinical-note drafts rather than confirmed records.

The proposed consultation draft must preserve who said what and must never turn an unverified patient statement into a confirmed clinical fact. It should distinguish:

- **Patient statements:** symptoms and history described by the patient.
- **Doctor questions:** questions asked during the consultation, not patient facts.
- **Examination findings:** observations entered or confirmed by the doctor.
- **Assessment:** a doctor-entered or doctor-confirmed assessment, never an independent AI diagnosis.
- **Doctor-approved plans:** tests, treatment, advice and follow-up approved by the doctor.

Extraction should detect negation, uncertainty, duration, frequency, associated details, multiple complaints, conflicting statements and missing information. For example, "I do not have fever" must not be extracted as fever being present. A medicine a patient cannot name must remain unknown and require verification. AI must produce an editable draft until the clinician reviews and approves the final record.

### 4.6 Medicine Catalogue and Prescription Assistance

- Search a verified, curated catalogue by generic or brand name.
- Display strengths, dosage forms, routes, manufacturers, provenance, and update dates.
- Create an editable draft containing medicine, strength, dose, route, frequency, duration, quantity, and instructions.
- Run deterministic checks for applicable allergies, known interactions, duplicate therapies, and missing information.
- Require a qualified doctor to confirm and sign the final prescription. AI must not prescribe or sign.

The medicine workflow should depend on a searchable, verified catalogue rather than model memory. Proposed catalogue fields include generic name, verified brand name, active ingredient, manufacturer, strength, dosage form, route, verified product and prescribing information, source and update date, relevant contraindications and reliable interaction or warning data.

Generic and brand search should support comparison of suitable catalogue entries. An editable prescription draft can contain medicine, strength, dose, route, frequency, duration, quantity and instructions. Available deterministic checks may identify allergies, known interactions, duplicate therapies and relevant patient factors. Missing or uncertain information must be displayed rather than inventing a dose or instruction.

The doctor must review and confirm the diagnosis or assessment, medicine, dose, frequency, duration and instructions before approving and signing the final prescription. AI must never independently prescribe or sign.

### 4.7 Patient Care Plan and Doctor's Instructions

- Convert the doctor's spoken or typed instructions into structured care-plan drafts.
- Categorize diet, lifestyle, activity restrictions, precautions, medication guidance, and follow-up.
- Preserve author, source encounter, date, status, and start/end date.
- Require clinician review before instructions become active.

The proposed care plan is separate from the clinical note and final prescription. A doctor may prepare or type instructions in structured categories:

- **Diet:** a doctor-advised dietary instruction or restriction.
- **Lifestyle:** a doctor-approved lifestyle recommendation.
- **Activity restriction:** a defined temporary or clinician-reviewed restriction.
- **Precaution:** warning signs or actions requiring attention.
- **Medication guidance:** an approved medicine timing or food-related instruction.
- **Follow-up:** a review date or recommended investigation.

Each instruction should preserve the exact approved wording or a doctor-approved equivalent, plus source consultation, author, date, status and start/end date where applicable. Statuses should include active, completed and discontinued. Changes and discontinuations require attribution and audit history. Expired restrictions must not automatically be treated as medical clearance; the clinician must reassess.

### 4.8 Clinical Notes and Restricted Doctor Notes

- Keep patient-facing instructions, the continuity-of-care note, and restricted clinician notes clearly separated.
- Apply explicit permissions and audits for restricted notes.
- Preserve clinically necessary access for authorized treating professionals.

Patient-facing care instructions, the continuity-of-care clinical record and narrowly restricted clinician notes must remain separate. Restricted notes require explicit permission and audit history. Clinically necessary information remains available to authorized treating professionals. The proposal does not allow routine pharmacy access to restricted notes or the full consultation record.

### 4.9 Follow-up and Care Continuity

- Record approved follow-up dates and recommended investigations.
- Track scheduling and completion status.
- Capture treatment response and adverse reactions.
- Display active, completed, and discontinued instructions without treating expiry as clearance.

## 6. Doctor's End-to-End Workflow

This proposed workflow is derived from the project proposal. It is not a claim of current implementation.

1. The patient is registered or identified through the hospital's approved identity process.
2. The patient books an appointment and joins the approved hospital queue.
3. The system retrieves only records authorized for the doctor and begins background preparation.
4. The doctor selects **Call Next Patient**; the correct patient and encounter open with a ready, partially ready, processing, failed, or no-records status.
5. The doctor reviews the source-linked briefing and opens exact reports or prior documents for verification.
6. The doctor confirms patient identity and consultation context to reduce wrong-patient risk.
7. The doctor starts consented audio recording or uses manual documentation.
8. Speech is transcribed into timestamped segments with speaker attribution and uncertainty markers.
9. AI creates structured, editable consultation-note, prescription, and care-plan drafts.
10. The system reconciles new statements with existing history and flags conflicts or missing information.
11. The doctor reviews and edits the assessment, notes, medicine draft, dose, route, duration, and care instructions.
12. The doctor approves and signs or authenticates the final clinical documents.
13. The patient receives only the approved prescription and appropriate care instructions.
14. Pharmacy receives an authorized dispensing view containing the necessary prescription and safety information, not the complete history or restricted notes.
15. Approved records, instruction status, and follow-up details are added to the chronological timeline with version and audit history.

The queue action must never start recording automatically. An incomplete or unavailable AI service must not prevent the doctor from continuing manually.

## 7. Proposed Technology Architecture

The following is a proposed architecture and technology direction, not an existing stack:

| Layer | Proposed technology or responsibility |
| --- | --- |
| Frontend | React, Vite, and Tailwind CSS for the doctor, patient, and pharmacy experiences |
| Backend | Python FastAPI for APIs, authentication integration, and workflow orchestration |
| Database | PostgreSQL for patients, encounters, medication records, notes, care plans, and audit data |
| Audio | Browser MediaRecorder API or another approved, secure capture mechanism |
| Speech recognition | Whisper or another evaluated clinical speech-recognition service or model |
| Speaker attribution | A model such as pyannote.audio, evaluated for the target setting |
| Generative AI | Structured-output LLM for extraction, summarization, reconciliation, and draft generation |
| Document processing | OCR and parsing with original-document and page-level references |
| Clinical safety | Deterministic, versioned rules using verified data and validated clinical criteria |
| Medicine catalogue | A curated or licensed catalogue with source and update provenance |
| Interoperability | ABDM-aligned FHIR R4 profiles where applicable |
| Document output | ReportLab or another controlled document-generation service |
| File storage | Private, encrypted object storage with access controls and retention policies |

The proposed FHIR-aligned records include:

- `Patient`
- `Encounter`
- `Condition`
- `AllergyIntolerance`
- `Observation`
- `DiagnosticReport`
- `DocumentReference`
- `MedicationStatement`
- `MedicationRequest`
- `CarePlan`
- `AuditEvent`

Supporting structures include `AudioAsset`, `TranscriptSegment`, `ClinicalNote`, `CareInstruction`, and `RestrictedNote`. Structured records are the proposed source of truth; AI summaries and vector-search results must not replace verified clinical data.

## 8. Academic MVP and Future Production Scope

The complete vision is larger than a typical academic project. The academic MVP should demonstrate one end-to-end hospital workflow using **synthetic patient data** and a limited, curated medicine catalogue.

### Proposed MVP capabilities

- Multiple synthetic patient identities and doctor accounts
- Synthetic patient history and chronological clinical timeline
- Selected sample report upload, extraction, and source-linked viewing
- Consent-aware audio recording and manual fallback
- Transcription and limited speaker attribution
- Structured consultation-note drafts
- A small curated medicine catalogue
- Selected deterministic safety checks
- Prescription drafts requiring doctor approval
- Care-plan and follow-up records
- Role-based access and audit demonstration

### Proposed MVP exclusions

The following are future expansion areas, not MVP commitments:

- Real hospital deployment or multi-hospital operations
- Consent-based external record exchange
- Large-scale validated document ingestion
- Production-grade multilingual clinical speech recognition
- Specialty-wide clinical validation
- Advanced clinical decision support
- A complete licensed medicine catalogue
- Comprehensive interaction and dosing support
- Production digital-signature infrastructure
- Integrated patient reminders or external provider workflows
- A production security, compliance, or regulatory assurance program

## 9. Security, Privacy, Clinical Safety and Compliance

- Obtain and record appropriate consent before audio recording, and provide a non-recording alternative.
- Allow recording to be paused or stopped; retain audio only according to defined consent and retention policies.
- Encrypt clinical information and recordings in transit and at rest.
- Apply tenant-aware, role-based, least-privilege authorization for every backend operation.
- Verify patient relationship and legitimate purpose before displaying clinical information.
- Record access, edits, exports, signing, sharing, dispensing, and approval events.
- Never silently overwrite an approved clinical note or prescription; use versioned corrections.
- Preserve source, date, author, and verification status for important facts.
- Distinguish patient-reported facts, imported records, clinician observations, and AI-generated drafts.
- Treat missing information as unknown, never as a negative finding.
- Prevent an LLM from inventing medicine data, doses, diagnoses, or clinical rules.
- Require human review and authorization before a prescription or care plan becomes final.
- Use validated, versioned clinical rules for critical alerts rather than assigning an autonomous Critical label through an LLM.
- Keep pharmacy access limited to the approved dispensing view and necessary safety information.
- Use synthetic data for the academic MVP. Real patient information must not be used without appropriate authorization and safeguards.

### Pharmacy Privacy and Minimum-Necessary Information

Pharmacy access should be limited to the approved prescription and the information required for lawful, safe dispensing. The minimum necessary view should include the approved medicine instructions, prescriber identity and required dispensing safety information. A pharmacist should not receive the complete clinical history, consultation transcript, unrelated reports or restricted doctor notes unless a backend-authorized, legitimate need exists.

The proposed authorization model is based on role, hospital or tenant, patient relationship and legitimate purpose. Backend authorization must enforce these boundaries; hiding a frontend screen is not sufficient. The system should record prescription viewing, dispensing, permitted substitution and clarification actions. Clarification requests should return to the prescriber through an auditable workflow.

### Compliance and Standards Boundary

The proposed design should consider:

- **HL7 FHIR R4** resources and concepts, including Patient, Encounter, Condition, AllergyIntolerance, Observation, DiagnosticReport, DocumentReference, MedicationStatement, MedicationRequest and CarePlan.
- Applicable published **ABDM implementation guidance** and consent-based health-information exchange requirements.
- **India EHR Standards 2016** considerations relating to electronic health records, prescription integrity, digital signatures and auditability.
- Applicable **Digital Personal Data Protection Act and Rules** obligations, including commencement dates, lawful processing, notice, security, retention and data-subject rights.

These are design considerations requiring later legal and implementation review. This README does not claim current regulatory, standards or legal compliance.

For clinical safety, the proposed priority levels are guidance for clinician attention, not autonomous diagnoses:

| Level | Proposed meaning |
| --- | --- |
| Critical | A potentially serious, time-sensitive issue supported by a validated rule or clearly documented source |
| Important | A clinically relevant allergy, medicine issue, prior condition, abnormal result, or unresolved follow-up |
| Contextual | Background history that may be useful but is not currently urgent |

Every priority finding must show its reason, source, date, verification state, and uncertainty. If the significance cannot be determined reliably, the system should request review rather than assigning unsupported risk.

## 10. Background Processing

Clinical preparation and document processing should run asynchronously so the queue and manual consultation workflow remain available. Proposed processing behaviour includes:

- Background jobs for record retrieval, OCR, document parsing, transcription, speaker attribution and clinical-draft preparation.
- Retries for transient failures and idempotent job or document-processing logic so duplicate processing or storage cannot accidentally occur.
- Partial results that remain visible while unfinished documents continue processing.
- Retry or manual-review controls for failed documents or services.
- Preservation of original uploads even if extraction or AI processing fails, subject to the configured retention policy.
- Processing logs that do not expose sensitive clinical content in ordinary application logs.
- No delay or AI-service failure that can block appointment, queue, consultation or prescription workflows.

The system must show processing status and uncertainty rather than fabricate a complete result or imply that unavailable records were reviewed.

## 11. Development Phases

| Phase | Proposed development work | Deliverable |
| --- | --- | --- |
| 1 | Patient records, encounters, allergies, medication history, and timeline | Patient-history module |
| 2 | Document upload, OCR, extraction, and source-linked viewer | Searchable report intelligence |
| 3 | Consent, audio capture, transcription, and diarization | Consultation recording module |
| 4 | Clinical extraction, summary, and history reconciliation | Structured consultation draft |
| 5 | Medicine catalogue, safety checks, and prescription draft | Doctor-reviewable prescription |
| 6 | Care plan, restricted notes, roles, and audit | Connected patient-care workflow |
| 7 | Integration, synthetic test cases, and evaluation | Demonstrable end-to-end academic MVP |

## 12. Testing and Acceptance Philosophy

Evaluation should use synthetic cases that include normal and difficult scenarios. Fast generation is not sufficient evidence of clinical quality; the project must report both efficiency and accuracy.

### Proposed test areas

- **Patient identity:** Wrong-patient record mixing and tenant isolation must be prevented.
- **Authorization:** Unauthorized roles must be denied restricted notes, full recordings, and unrelated histories.
- **Document extraction:** Compare extracted values, units, dates, and findings with original documents.
- **Source navigation:** Verify exact document, page, section, or region references.
- **Transcription:** Measure word error and clinically important transcription error.
- **Speaker attribution:** Verify separation of doctor, patient, and uncertain speech; test corrections and audit history.
- **Clinical extraction:** Test negation, uncertainty, duration, multiple complaints, conflicting statements, and missing details.
- **History retrieval:** Measure relevant-record recall while avoiding irrelevant or outdated overemphasis.
- **Safety checks:** Test known allergy, duplicate therapy, interaction, missing-information, and false-alert scenarios.
- **Trend comparison:** Reject unsafe unit or method comparison and preserve original reported values.
- **Workflow performance:** Measure queue briefing preparation and reviewable-draft creation time.
- **Human review:** Measure corrections needed before clinician approval.
- **Privacy:** Test backend permission boundaries and audit events, not only hidden frontend controls.
- **Failure handling:** Verify partial results, retries, idempotency, stale data, processing failures, and manual continuation.
- **Audio consent:** Verify that recording cannot begin without the required action and consent context.
- **Wrong-patient isolation:** Verify that no record is attached or displayed for the wrong patient or encounter.
- **Tenant isolation:** Verify that one hospital or tenant cannot access another tenant's records.
- **AI failure:** Verify that incomplete, failed or unavailable AI processing does not block the queue or manual documentation.
- **Clinician approval:** Verify that generated notes, prescriptions and care instructions remain drafts until explicitly approved and signed or authenticated.
- **Pharmacy restrictions:** Verify backend denial of restricted notes and unrelated patient history.
- **Audit history:** Verify that viewing, correction, approval, export and dispensing actions remain attributable.

### Acceptance principles

- Calling the next patient must open the correct patient and encounter and must never start recording automatically.
- The doctor must be able to continue if AI preparation is incomplete or unavailable.
- AI-generated notes and prescriptions must remain drafts until clinician approval.
- Every high-priority finding must include its source, date, reason, and verification state.
- The doctor must be able to open the supporting record and verify any extracted finding.
- Current medicines must be distinguishable from historical prescriptions.
- Transcript and speaker-label corrections must be auditable.
- Instructions must have an author, source, date, status, and review trail.
- Pharmacy accounts must not receive restricted notes or unrelated history.
- Acceptance must report false warnings, missed warnings, unsupported statements, missed facts, and required clinician corrections.

## 13. Proposed Interoperability and Standards Considerations

The proposal recommends considering:

- **HL7 FHIR R4**, including applicable Patient, Encounter, Condition, AllergyIntolerance, Observation, DiagnosticReport, DocumentReference, MedicationStatement, MedicationRequest, and CarePlan concepts.
- **ABDM** consent-based health-information exchange and applicable implementation guidance.
- **India EHR Standards 2016** for electronic records, prescription integrity, digital signatures, and auditability.
- Applicable **Digital Personal Data Protection Act** and Rules requirements.
- **Clinical AI governance** principles, including clinician oversight, traceability, validation, risk management, and ongoing monitoring.

These standards are design considerations for a future product and do not indicate compliance or implementation.

## 14. Expected Outcome and Future Scope

The intended academic outcome is a working prototype that connects patient history, document analysis, ambient consultation documentation, prescription drafting, and patient-care instructions. The proposed benefit is faster, better-organized access to relevant historical information and less repetitive manual documentation, while preserving professional review and control.

Future scope may include ABDM/ABHA-enabled consent-based exchange, additional Indian languages, evaluated medical speech recognition, laboratory and pharmacy integrations, a larger verified medicine catalogue, patient follow-up features, clinical validation, security assessment, and regulatory review. Real-world deployment should proceed only after appropriate clinical, security, privacy, and regulatory validation.
