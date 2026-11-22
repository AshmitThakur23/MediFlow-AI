# MediFlow AI Implementation Roadmap

**Last updated:** 2026-11-22

This roadmap is the persistent, chunk-by-chunk implementation checklist for
MediFlow AI. Update this file after each completed task with actual changes and
test evidence. Do not mark work complete until repository evidence exists.

No roadmap item overrides `README.md`, `AGENTS.md`, the database schema design,
or an unresolved proposal decision.

## Overall Progress

- **Completed:** approximately 20%
- **Remaining:** approximately 80%
- **Current stage:** Database models and integrity checks
- **Next stage:** API foundation

The percentage is a planning estimate based on repository implementation
coverage. It is not a formal project-metrics result.

## Verification Legend

- `[x]` Implemented and verified
- `[~]` Started but not complete
- `[ ]` Not started
- `Evidence`: command output, tests, source inspection, or other repository proof

## Chunk 0 — Project Documentation and Engineering Policy

- [x] Create the MediFlow AI workspace directory.
- [x] Create and maintain the project README.
- [x] Create persistent agent and engineering instructions.
- [x] Create the architecture assessment.
- [x] Create technology decision and radar records.
- [x] Create the database schema design.
- [x] Establish synthetic-data and human-approval boundaries.

**Evidence:**

- Approved project documentation exists in `README.md`, `AGENTS.md`, and
  `docs/`.
- Clinical AI safety and permanent project-memory rules are documented.

## Chunk 1 — SQLAlchemy and Core Database Foundation

- [x] Configure the Python backend and SQLAlchemy base.
- [x] Register the database engine and session infrastructure.
- [x] Implement `Hospital`.
- [x] Implement `User`.
- [x] Implement `HospitalUser`.
- [x] Implement `Patient`.
- [x] Enable SQLite foreign-key enforcement in model tests.

**Evidence:**

- Core model files exist under `backend/app/models/`.
- Core models are exported through `backend/app/models/__init__.py`.
- The complete core-model test file passes with synthetic fixtures.

## Chunk 2 — Patient Identity and Matching

- [x] Implement `PatientIdentifier`.
- [x] Implement `PatientMatchCandidate`.
- [x] Implement same-hospital composite patient integrity.
- [x] Implement identifier, review, and confidence constraints.
- [ ] Implement patient search APIs.
- [ ] Implement patient merge APIs.

**Evidence:**

- Model implementation and tests exist in the backend model and test modules.
- API and merge workflow implementation are not present.

## Chunk 3 — Appointments and Encounters

- [x] Implement `Appointment`.
- [x] Implement `Encounter`.
- [x] Implement tenant-qualified patient and doctor assignments.
- [x] Implement status and time constraints.
- [x] Implement encounter/patient and appointment/patient integrity.
- [ ] Implement appointment APIs.
- [ ] Implement encounter APIs.
- [ ] Implement queue integration.

**Evidence:**

- SQLAlchemy models, relationships, constraints, and tests exist.
- Queue sessions and queue entries remain blocked pending boundary approval.

## Chunk 4 — Provenance and Typed Clinical Records

- [x] Implement `ProvenanceRecord`.
- [x] Implement `Condition`.
- [x] Implement `AllergyIntolerance`.
- [x] Implement `Observation`.
- [x] Implement `MedicationStatement`.
- [x] Implement encounter-patient and provenance-patient integrity.
- [x] Implement hospital-level provenance and encounter-linked provenance rules.
- [ ] Implement provenance APIs.
- [ ] Implement typed clinical-record APIs.
- [ ] Implement clinical history timeline APIs.

**Evidence:**

- Latest complete core-model result: `75 passed in 1.77s`.
- Compilation passed for `backend/app` and `backend/tests/test_core_models.py`.
- Provenance polymorphic source validation remains a future application boundary.
- `medicine_catalogue_items` remains unimplemented, so medication catalogue
  references do not create an FK yet.

## Chunk 5 — API and Authentication Foundation

- [x] Implement FastAPI application routing.
- [x] Implement local synthetic academic-MVP authentication.
- [x] Implement hospital/tenant authorization.
- [x] Implement reusable exact-role-code authorization.
- [x] Implement patient relationship and legitimate-purpose checks.
- [x] Implement standard API validation and error responses.
- [x] Add authentication and tenant-isolation tests.
- [x] Add API integration tests for authentication, tenant, and patient-boundary behavior.

**Evidence:**

- Added PBKDF2-HMAC-SHA256 password hashing with random salts and 600,000
  iterations.
- Added `/api/v1/auth/login` and `/api/v1/auth/me`.
- `/auth/me` supports HTTP Basic credentials and requires `X-Hospital-Id`
  tenant-assignment verification.
- Active hospital assignments must be in their valid date period.
- `/auth/me` requires `X-Mediflow-Purpose` and validates the value as a bounded
  legitimate-purpose header.
- Exact `role_code` matching is available for future route dependencies.
- Hospital-scope assignments may access patient objects in their hospital.
  Department and patient_relationship scopes fail closed because no approved
  patient-relationship model exists yet.
- Authentication tests passed repeated runs:
  `10 passed` on 2026-11-22.
- Authorization and tenant tests passed:
  `10 passed` on 2026-11-22.
- Final combined verification passed:
  `95 passed in 23.26s`.
- Complete core-model suite passed:
  `75 passed in 1.76s`.
- Python compilation passed for `backend/app` and `backend/tests`.
- This is an academic-MVP identity boundary, not production authentication.

**Next task recommendation:** Complete role and permission enforcement, then
expose patient and encounter APIs.

## Chunk 6 — Patient and Encounter REST Workflows

- [x] Implement patient profile APIs.
- [~] Implement patient search and identity-match review APIs.
- [x] Implement appointment scheduling and check-in APIs.
- [x] Implement encounter start and completion APIs.
- [~] Implement longitudinal patient timeline APIs.
- [x] Implement wrong-patient and cross-hospital isolation tests.

**Evidence:**

- Added tenant-scoped patient create, search, and get APIs.
- Added tenant-scoped appointment create, list, get, and status APIs.
- Added tenant-scoped encounter create, list, get, and status APIs.
- Added a patient schedule timeline containing appointments and encounters.
- Added application-level patient/appointment same-patient validation.
- Added cross-hospital patient, appointment, and encounter isolation tests.
- Focused Chunk 6 suite passed repeatedly:
  `9 passed`.
- Combined API, authentication, and core suite passed:
  `93 passed in 18.86s`.
- Python compilation passed.
- Identity-match candidate review and a clinical longitudinal fact timeline
  remain future work in later chunks.

## Chunk 7 — Provenance and Clinical History APIs

- [x] Implement provenance creation and retrieval APIs.
- [x] Implement condition APIs.
- [x] Implement allergy APIs.
- [x] Implement observation APIs.
- [x] Implement medication statement APIs.
- [x] Implement supersession and historical-version APIs.
- [x] Prevent AI or automation from approving clinical records.

**Evidence:**

- Added tenant-scoped provenance create and list APIs.
- Added tenant-scoped condition, allergy, observation, and medication APIs.
- Added patient and encounter consistency validation before persistence.
- Added same-hospital/same-patient supersession validation.
- Preserved polymorphic `source_record_id` without a false ordinary foreign key.
- Preserved unresolved uncertainty vocabulary without introducing a value allow-list.
- Added typed facts to the synthetic patient schedule/history timeline.
- AI and autonomous clinical approval behavior were not implemented.
- Chunk 7 suite passed repeatedly:
  `9 passed`.
- Combined Chunk 5, 6, 7, and core suite passed:
  `104 passed in 33.13s`.
- Python compilation passed.

## Chunk 8 — Medicine Catalogue and Prescription Support

- [x] Implement `MedicineCatalogueItem`.
- [x] Implement catalogue source, synthetic-data, and version metadata.
- [x] Implement catalogue search.
- [x] Link medication statements and prescription lines safely.
- [x] Implement prescription-draft models and APIs.
- [x] Implement deterministic, reviewed safety checks.
- [x] Require clinician review and approval.
- [x] Implement the pharmacy minimum-necessary view.

**Evidence:**

- Added synthetic catalogue metadata and catalogue search APIs.
- Added prescription draft, draft-line, signed-prescription, prescription-line,
  dispensing-record, and dispensing-line models.
- Medication statements now use the catalogue foreign key only for real catalogue items.
- Draft approval and signing require a doctor; signing is never performed by AI.
- Pharmacy access is restricted to signed prescription, lines, and dispensing state.
- Deterministic checks are limited to exact allergy-name and active-medication
  duplicate review; no interaction engine or clinical interpretation is claimed.
- Chunk 8 suite passed repeatedly:
  `7 passed`.
- Combined core/auth/clinical/prescription suite passed:
  `111 passed in 45.49s`.
- OpenAPI verified 7 Chunk 8 route families.
- Catalogue licensing, external data provenance, and interaction datasets remain
  unresolved and are not represented as verified clinical sources.

## Chunk 9 — Documents, OCR, and Source Viewing

- [~] Implement secure document upload and metadata.
- [ ] Implement encrypted object storage integration.
- [ ] Implement file type and malware validation.
- [x] Implement document and page models.
- [ ] Implement OCR and parsing jobs.
- [x] Preserve page, text, region, and uncertainty references.
- [x] Implement human extraction correction and verification.
- [~] Implement source navigation.

**Evidence:**

- Added tenant-scoped `MedicalDocument`, `DocumentPage`, `DocumentRegion`,
  `DocumentExtraction`, and `DocumentExtractionCorrection` models.
- Added document metadata, page, region, extraction, and correction APIs.
- MIME allow-list and SHA-256 metadata validation are implemented.
- `object_uri` is stored as a reference only; no credential, encrypted object,
  binary upload, or malware scan is claimed.
- Region-to-document mismatches are rejected in application transactions.
- Corrections are append-only and require a doctor assignment.
- Chunk 9 suite passed repeatedly:
  `6 passed`.
- Combined current backend suite passed:
  `117 passed in 52.43s`.
- Python compilation and SQLite DDL creation passed with foreign-key enforcement.
- OCR providers, OCR quality, selectable-text parsing, background jobs,
  encrypted storage, malware scanning, and provider/format approval remain
  unresolved.

## Chunk 10 — Consultation Recording and Transcription

- [~] Implement consent-aware browser microphone capture with MediaRecorder.
- [~] Implement real-time Chrome Web Speech transcript capture.
- [ ] Store timestamped transcript text in the local MVP backend.
- [ ] Allow pause, stop, restart, and manual-documentation fallback.
- [ ] Display uncertain or interrupted transcription visibly.
- [ ] Preserve original and corrected transcript text for review.
- [ ] Do not claim speaker diarization or production-grade transcription.

**API-first 4-hour MVP scope:**

- Browser recording and Chrome Web Speech are the first implementation target.
- Transcript text is submitted to the server for Gemini draft generation.
- No custom speech model, custom diarization model, queue engine or audio
  encryption service is required for the academic demonstration.

**Verified implementation evidence:**

- Browser voice capture UI is implemented with Chrome Web Speech and manual
  transcript editing.
- Browser MediaRecorder creates a playable local audio preview.
- The transcript is editable and is sent to the server for Gemini analysis.
- The MVP does not implement speaker diarization or production audio storage.
- The clinical-note template is predefined and can be saved or approved through
  `ClinicalNoteDraft` database records.
- The exact consultation transcript is printed in the A4 prescription draft.
- Gemini fills only the structured template fields; missing doses and
  instructions remain explicit missing-data entries.
- Server Gemini route is implemented and registered.
- Live verified Gemini call used `gemini-2.5-flash` and returned structured
  JSON with `clinical_approval_required=true`.
- The key is required only in `backend/.env`; it is excluded from Git by
  `backend/.gitignore`.

## Chunk 11 — AI Clinical Drafting and Briefings

- [x] Configure Gemini 2.5 Flash through a server-only `GEMINI_API_KEY`.
- [~] Implement structured JSON generation for chief complaint and history.
- [ ] Separate patient-reported facts, doctor questions and examination findings.
- [ ] Generate editable consultation-note drafts.
- [ ] Preserve negation, uncertainty, missing information and contradictions.
- [ ] Generate prescription and medicine candidates only as reviewable drafts.
- [ ] Preserve source-linked structured history rather than replacing it.
- [ ] Require explicit doctor review for every generated draft.
- [ ] Prohibit Gemini-generated diagnosis, prescription, signing or approval.

**API-first 4-hour MVP scope:**

- Gemini is used for structured extraction and editable draft generation.
- Gemini is not used for autonomous clinical decisions.
- The API key is stored in `backend/.env` as `GEMINI_API_KEY=...`.
- Do not place the key in React code, source files, screenshots or chat.
- The UI must display loading, unavailable and failure states honestly.

**Verified implementation evidence:**

- `/api/v1/ai/clinical-draft` is registered and uses server-only Gemini SDK code.
- A real synthetic transcript was successfully converted by Gemini 2.5 Flash
  into a structured draft with a chief complaint and prescription draft fields.
- A real prescription-heavy synthetic transcript produced two medicine candidates
  and explicitly listed missing strength, dose, route, frequency, duration and
  quantity fields instead of inventing them.
- The route returns `503` when `GEMINI_API_KEY` is missing.
- The prompt prohibits diagnosis, prescribing, signing and clinical approval.

## Chunk 12 — React Frontend

- [x] Set up React and Vite with TypeScript.
- [~] Implement authentication and role-aware screens.
- [~] Implement patient search and timeline.
- [~] Implement appointment and encounter workflows.
- [~] Implement source-linked briefing states.
- [~] Implement consent-aware consultation documentation.
- [x] Implement clinical-note editor and doctor-reviewable draft UI.
- [x] Implement prescription draft review UI.
- [~] Implement one unified A4 clinical/prescription record print template.
- [ ] Implement the pharmacy minimum-necessary view.

**Evidence:**

- The frontend is in `frontend/`.
- Synthetic login connects to the local FastAPI login endpoint.
- Patient search is accessible through the existing tenant-scoped backend API.
- The polished MVP shell includes the doctor queue, selected patient,
  briefing, clinical-note draft, and prescription-review screens.
- Production build and lint pass.
- AI and clinical approval actions are presentation-only demonstrations,
  not autonomous diagnosis or treatment behavior.
- Full backend-driven navigation and all role-specific screens remain
  incomplete.
- Dynamic morning, afternoon and evening greetings are implemented.
- The clinical-note workspace includes voice capture, editable transcript,
  Gemini generation and human-review controls.
- The unified A4 print template includes the exact transcript, clinical note
  template, structured prescription fields and clinician/approval boundaries.
- Dynamic morning, afternoon and evening greeting text is implemented.
- The clinical workspace is live-polling the backend every 15 seconds.
- Real Gemini verification produced a structured dry-cough chief complaint,
  one medicine candidate, missing prescription fields, and
  `clinical_approval_required=true`.
- Browser verification confirmed login, patient selection, appointment check-in,
  Gemini clinical-draft generation, database save and approval of a clinical
  note, prescription draft creation, approval and synthetic signing.
- The clinical-note Save action writes to `ClinicalNoteDraft`; browser
  `localStorage` is no longer used for clinical note templates.
- The clinical and prescription A4 print views use the exact edited
  transcript/template values and explicitly label draft-only status.

## Chunk 13 — Security, Audit, and Operations

- [ ] Implement consent records and audit events.
- [ ] Implement record versioning and correction history.
- [ ] Implement encryption, secret, and retention configuration.
- [ ] Generate and apply reviewed Alembic migrations.
- [ ] Configure PostgreSQL for development and testing.
- [ ] Verify migrations and foreign-key behavior on PostgreSQL.
- [ ] Implement backups and disaster-recovery procedures.
- [ ] Implement deployment configuration.

## Chunk 14 — Integration and Acceptance Verification

- [ ] Run complete backend tests.
- [ ] Run frontend tests.
- [ ] Run API integration tests.
- [ ] Test cross-hospital isolation.
- [ ] Test cross-patient isolation.
- [ ] Test consent and authorization boundaries.
- [ ] Test AI draft versus approved-record boundaries.
- [ ] Run synthetic end-to-end workflow testing.
- [ ] Test failure, retry, partial-result, and manual-fallback behavior.
- [ ] Review PostgreSQL behavior.
- [ ] Prepare the academic MVP verification report.
