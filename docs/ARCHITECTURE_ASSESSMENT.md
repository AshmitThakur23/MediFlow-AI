# MediFlow AI — Initial Architecture Assessment

**Status:** Initial proposal assessment for academic MVP design. No implementation is confirmed.

**Scope:** This document separates requirements derived from `MediFlow_AI_Final_Checked.docx` and `README.md` from preliminary technical recommendations. It does not finalize architecture, select production vendors or claim clinical or regulatory readiness.

## 1. Purpose and Assessment Boundary

MediFlow AI is proposed as an academic hospital-workflow prototype that connects patient history, current consultation documentation and future care. The MVP must use synthetic patient data and a limited curated medicine catalogue.

The architectural objective is to demonstrate one end-to-end workflow:

1. Identify and queue a patient.
2. Prepare a source-linked background briefing.
3. Record or manually document an authorized consultation.
4. Create clinician-reviewable note, medicine and care-plan drafts.
5. Approve and sign the clinical documents.
6. Provide a minimum-necessary pharmacy view.
7. Persist the approved encounter and follow-up information.

AI-generated records remain drafts. AI must never independently diagnose, prescribe, sign or approve treatment.

## 2. Proposal-Aligned System Architecture

The proposal names these architectural directions rather than confirmed implementation choices:

- React, Vite and Tailwind CSS frontend
- Python FastAPI backend
- PostgreSQL relational database
- Browser MediaRecorder or approved audio capture
- Evaluated speech recognition and speaker diarization
- Structured-output generative AI
- OCR and document parsing
- Deterministic, versioned clinical-safety rules
- Curated medicine catalogue
- ABDM-aligned FHIR R4 interoperability
- Private encrypted object storage
- Controlled PDF generation

A suitable conceptual academic architecture is a modular web application with one or more independently deployable API and worker processes:

```text
[Doctor / Patient / Pharmacy web UI]
              |
        API Gateway / Backend
              |
  [Identity & Authorization]  [Clinical API]
              |                     |
      [PostgreSQL]          [Document / Media Services]
              |                     |
     [Audit & Versioning]    [Object Storage / Job Queue]
                                    |
                     [OCR | ASR | Diarization | LLM
                      | Deterministic Safety Rules]
                                    |
                     [Structured source-linked records]
```

This is a recommendation for assessment purposes, not an implemented architecture. Each boundary should be enforced in backend code and independent of UI behavior.

## 3. Frontend and Backend Responsibilities

### Frontend

**Proposal requirement**

- Provide doctor queue and call-next workflows.
- Show source-linked briefing status and original evidence.
- Provide a consent-aware consultation room.
- Provide a clinical-note editor, prescription workspace and care plan.
- Provide a minimum-necessary pharmacy view.
- Preserve clear separation between AI drafts and clinician-approved records.

**Data flow**

1. Authenticated user requests a permitted resource.
2. Backend validates role, tenant, patient relationship and purpose.
3. Frontend renders backend-authorized data.
4. Clinician submits draft edits and explicit approval actions.
5. Recording starts only after separate consent-aware action.

**Dependencies**

- Identity provider or academic authentication integration
- Backend API contract
- Secure browser audio and file-upload support
- PDF/image viewer capabilities
- Audit event submission

**Risks**

- Frontend-only authorization creates tenant or record leakage.
- AI confidence may be visually mistaken for clinical certainty.
- Transcript or draft attribution may become ambiguous.
- Wrong-patient operations may expose or modify the wrong encounter.

**Alternatives**

- React + Vite is compatible with component-based interaction and is a proposal direction.
- A server-rendered framework could reduce client complexity, but must still separate access rules and source evidence.
- Material component libraries could standardize UI but are not required by the proposal.

React documentation describes component-based UI construction and state rendering; FastAPI documents typed Python APIs, OpenAPI and JSON Schema integration. These official sources support a React/FastAPI direction but do not prove it is appropriate for every academic deployment. [1][2]

**Decision awaiting approval**

- Approved for the academic MVP: React, Vite, TypeScript and Tailwind CSS.
- Confirm browser storage rules and whether local prototype authentication is acceptable for MVP demonstration.

### Backend

**Proposal requirement**

- Expose APIs for identity, encounters, history, documents, queue, audio, transcripts, drafts, approvals and audits.
- Orchestrate asynchronous processing.
- Apply authorization and tenant isolation before every clinical operation.
- Create versioned, audited clinical records.

**Data flow**

Web client → API authentication → tenant/patient authorization → service function → PostgreSQL/object storage/job queue → audit event.

**Dependencies**

- PostgreSQL
- Secure object storage
- Job queue and worker runtime
- Identity integration
- Document and AI providers
- PDF output service

**Risks**

- API over-broadness may bypass purpose and relationship checks.
- Synchronous AI calls may block queue workflows.
- Approval endpoints may allow unsigned or unauthorized state changes.
- Background job retries may duplicate or mix clinical records.

**Alternatives**

- FastAPI is a proposal-compatible typed Python API framework with OpenAPI support.
- Django REST Framework offers stronger built-in conventions and admin tooling but may add framework complexity.
- A modular monolith is likely more appropriate for the academic MVP than a distributed microservice system.

**Decision awaiting approval**

- Approved for the academic MVP: Python and FastAPI in a modular monolith.
- Approve API authentication technology and its synthetic-user model.

## 4. Clinical Data Storage and Longitudinal Patient History

### Purpose

Maintain a chronological, source-preserving timeline of synthetic encounters, conditions, allergies, medication statements, requests, observations, reports, documents, notes, instructions and follow-up.

### Data flow

Document or encounter → normalized structured record → timeline projection → source-linked review → approved version → audit event.

### Dependencies

- PostgreSQL
- FHIR-aligned data model
- Identity/tenant identifiers
- Document storage identifiers
- Versioning and audit schema

### Risks

- Duplicate patients or tenant data mixing.
- Silent overwrite of approved records.
- Confusing patient-reported, clinician-confirmed and AI-generated facts.
- Missing information interpreted as a negative finding.
- Historical units or test methods incorrectly compared.

### Storage recommendation

Use PostgreSQL for the proposal-aligned structured source of truth and encrypted object storage for original documents and recordings. PostgreSQL official documentation should guide transactions, constraints and migrations if implementation begins. [3]

Keep:

- Append-only audit events
- Record and approval versions
- Explicit status and verification fields
- Source document references
- Page/region coordinates when supported
- Author, encounter and tenant identifiers

Do not store AI summaries as the only copy of a clinical fact. Use the data model entities identified in the proposal, including Patient, Encounter, Condition, AllergyIntolerance, Observation, DiagnosticReport, DocumentReference, AudioAsset, TranscriptSegment, ClinicalNote, CareInstruction, RestrictedNote, ConsentRecord and AuditEvent.

### Alternatives

- PostgreSQL + normalized tables: strongest fit for relational integrity and academic queryability.
- FHIR-native server: better interoperability but adds profile and implementation-guide complexity.
- Document database: flexible but weaker for relational authorization, versioning and referential integrity.

**Decision awaiting approval**

- Approved for the academic MVP: PostgreSQL as the primary structured source of truth.
- Approve whether the MVP stores FHIR resources natively or uses a FHIR-compatible internal model with controlled mapping.

## 5. Medical Document Upload, OCR and Extraction

### Purpose

Accept laboratory, radiology, prescription, discharge, operation and other supported documents; extract text and relevant fields; preserve source navigation and uncertainty.

### Data flow

Upload → virus/type validation → encrypted original storage → metadata record → queued OCR/parsing → page or region extraction → uncertainty review → approved structured facts.

### Dependencies

- Private object storage
- OCR/parser
- Source and page reference model
- Image/PDF viewer
- Approved document catalogue
- Human correction workflow

### Risks

- Handwriting or unclear scans.
- OCR unit or decimal errors.
- Page or table-region mismatch.
- Summary replacing the original evidence.
- Document date confusion.
- Duplicate processing.
- Cross-patient or cross-tenant upload.

### Alternatives

- Cloud managed OCR may provide better scale and forms support but requires privacy, licensing and data-processing review.
- Open-source OCR may reduce vendor dependency but requires quality evaluation and packaging.
- PDF text extraction should be preferred before OCR where text is selectable.
- Hybrid processing may combine selectable text, OCR and human correction.

**Recommendation**

For the MVP, use a hybrid and source-preserving pipeline: preserve the original, identify document type and metadata, attempt text extraction, mark confidence and uncertainty, store page and bounding-box references where supported, and require clinician verification.

Do not infer a diagnosis from radiology imaging alone.

**Decision awaiting approval**

- Select one OCR parser for the MVP.
- Approve whether managed or local processing is acceptable for synthetic documents.
- Approve supported document formats and maximum sizes.

## 6. Consultation Recording, Transcription and Speaker Identification

### Purpose

Capture consented consultation audio, create timestamped transcripts and propose speaker labels while preserving uncertainty and manual fallback.

### Data flow

Separate consent-aware start action → browser audio capture or approved mechanism → encrypted audio upload → consent and retention metadata → transcription job → diarization job → timestamped segments and confidence → clinician correction → approved documentation.

### Dependencies

- Browser capture or approved capture mechanism
- Consent record
- Speech recognition
- Diarization
- Secure audio storage
- Original and corrected transcript versions

### Risks

- Recording without consent.
- Incorrect patient or encounter association.
- Diarization falsely treated as identity.
- Overlapping speech, accents and code-switching.
- Sensitive audio retained too long.
- Transcript facts incorrectly converted to confirmed findings.

### Alternatives

- Browser MediaRecorder: proposal-compatible and deployable for an MVP, but browser support and transport security require evaluation.
- Managed transcription: may improve accuracy but requires privacy and data-processing review.
- Whisper or another evaluated model: needs target-setting quality evaluation.
- pyannote.audio or another diarization model: probabilistic output and licensing/runtime compatibility require evaluation.

**Decision awaiting approval**

- Approve the MVP capture mechanism.
- Approve whether recording remains local or uses an external service.
- Approve retention duration and deletion behavior.
- Approve the target languages and clinical scenarios.

## 7. AI Clinical Extraction and Doctor Briefing

### Purpose

Convert evidence from history and consented conversation into reviewable structured drafts and a queue-connected source-linked briefing.

### Data flow

Authorized records → retrieval/filtering → document and transcript processing → structured extraction → context reconciliation → source-linked draft and briefing → deterministic checks → clinician review.

### Dependencies

- Retrieval service
- Structured medical history
- Document extracts
- Transcript segments
- Structured-output generative AI
- Deterministic rules
- Provenance model

### Risks

- Unsupported risk labels.
- Hallucinated findings or medicines.
- Negation and uncertainty errors.
- Stale or inaccessible records appearing complete.
- Inappropriate emphasis on irrelevant history.
- Prompt or model updates changing clinical output.
- Cross-patient retrieval contamination.

### Briefing states

The proposal requires Ready, Partially ready, Processing, Failed, No records available and Stale data. The approximately 20–30-second figure is an engineering target for routine indexed cases, not a guaranteed clinical result.

### Alternatives

- External hosted structured-output LLM: fastest MVP integration but requires vendor privacy, model-version and prompt-evaluation controls.
- Local open model: stronger data-control option but requires hardware and quality evaluation.
- Retrieval and extraction can use retrieval-augmented generation, but verified structured records must remain authoritative.

**Recommendation**

Use structured extraction schemas with explicit provenance and uncertainty. Keep deterministic checks separate from generative AI. Test source retrieval and prompt/model versions. AI output must remain a draft.

**Decision awaiting approval**

- Approve one or more candidate AI providers or local models.
- Approve minimum structured-output and evaluation requirements.
- Approve whether generative AI may be used only for extraction/drafting, with no clinical rule assignment.

## 8. Medicine Catalogue and Prescription Assistance

### Purpose

Search verified generic and brand medicines, draft structured prescriptions and display supported allergy, interaction and duplicate-therapy warnings.

### Data flow

Curated catalogue → generic/brand search → selected catalogue item → patient context → deterministic checks → editable prescription draft → doctor approval/signing → approved prescription and dispensing view.

### Dependencies

- Licensed or curated catalogue
- Provenance and update process
- Allergy and medication statements
- Deterministic interaction/contraindication engine
- Approval and signing workflow

### Risks

- Model-provided medicine facts instead of verified catalogue facts.
- Missing dose or instruction invented by AI.
- Outdated catalogue data.
- Unsafe interaction rules.
- Duplicate therapy misclassification.
- Unauthorized pharmacy exposure.

### Alternatives

- Small hand-curated synthetic catalogue for academic MVP.
- Licensed commercial catalogue for future use.
- Locally maintained Indian medicine reference data would require provenance, licensing and update governance.

**Recommendation**

Use a small, explicitly versioned synthetic/curated catalogue for the MVP. AI must only create an editable draft. Clinical approval and signing remain exclusively with the doctor.

**Decision awaiting approval**

- Approve the MVP catalogue source and update process.
- Approve which deterministic checks are demonstrable.
- Approve the signing and authentication mechanism for the academic MVP.

## 9. Care Plans, Follow-up and Clinical Notes

### Purpose

Separate patient-facing instructions, continuity-of-care notes and restricted clinician notes; track active, completed and discontinued care instructions and follow-up.

### Data flow

Consultation transcript/document inputs → structured draft categories → clinician review → approved instruction or note → versioned timeline record → follow-up scheduling/completion.

### Dependencies

- ClinicalNote and CarePlan entities
- CareInstruction lifecycle
- RestrictedNote permissions
- Encounter linkage
- Audit and version history

### Risks

- Restriction automatically treated as continuing indefinitely.
- Expired restriction misclassified as clearance.
- Extra restrictions invented by AI.
- Follow-up date lost or incorrectly duplicated.
- Restricted notes exposed through an API or export.

### Alternatives

- Separate relational entities for care plan and instruction entries are stronger for lifecycle management.
- A free-text-only care plan is simpler but does not support status and audit needs.
- An external workflow engine is unnecessary for the academic MVP.

**Recommendation**

Use separate typed instruction records with author, source encounter, date, status and start/end dates. Require clinician confirmation before active status.

**Decision awaiting approval**

- Approve the care-plan data lifecycle fields and status transitions.
- Approve the synthetic follow-up workflow.

## 10. Authentication, RBAC, Tenant Isolation and Audit

### Purpose

Control access to patients and clinical functions according to role, hospital tenant, patient relationship and legitimate purpose.

### Data flow

Login → authenticated principal → tenant/role context → backend authorization policy → permitted operation → audit event.

### Dependencies

- Identity provider or academic authentication
- Tenant and patient relationship model
- Authorization middleware/policy
- Audit store
- Session and token handling

### Risks

- Tenant ID from client input.
- Missing object-level authorization.
- Over-broad roles.
- Pharmacy access to unrestricted history.
- Audit events containing sensitive data.
- Shared synthetic accounts making attribution impossible.

### Alternatives

- Hosted identity provider: better OAuth/OpenID Connect conventions but requires account setup.
- Local academic authentication: simpler demonstration but must not be represented as production-ready.
- Attribute-based authorization: flexible for hospital, relationship and purpose but more complex.
- RBAC with backend tenancy and object-level relationship checks: proportionate MVP approach.

The OWASP Application Security Verification Standard provides a framework for application security requirements and testing, but the MVP should target only documented and evidenced controls, not claim full ASVS compliance. [4]

**Recommendation**

Use backend RBAC plus mandatory tenant and patient relationship checks on every clinical read and mutation. Encrypt data in transit and at rest and use least-privilege service roles. Preserve audit events for access, edits, exports, approval, signing and sharing.

**Decision awaiting approval**

- Approve the MVP identity mechanism.
- Approve role names and permissions.
- Approve tenant and relationship model.
- Approve which audit fields and retention periods are demonstrable.

## 11. Background Processing and Failure Handling

### Purpose

Prepare briefings and process uploads/transcripts asynchronously without blocking the queue or prescription workflow.

### Data flow

API event → durable job record → queue → worker → provider/service call → result or partial result → status update → notification or polling.

### Dependencies

- Job queue
- Worker runtime
- Idempotency keys
- Retry policy
- Status data
- Original storage
- Dead-letter or manual-review process

### Risks

- Duplicate document processing.
- Retry after partial write.
- Stale status.
- Sensitive payloads in logs.
- Provider delay blocking the queue.
- Job consuming data from an unauthorized tenant.
- Retrying AI output with changed prompt or model.

### Alternatives

- Managed job queue/service: operationally simpler but introduces vendor and cost decisions.
- Embedded task queue: faster for a local academic MVP but weaker durability.
- Scheduled polling: simple but less responsive.
- A worker plus persistent job records and idempotency keys is recommended for proposal alignment.

**Recommendation**

Process asynchronously, retain original uploads, display partial and stale states, retry transient failures, make operations idempotent and permit manual continuation.

**Decision awaiting approval**

- Approve job queue technology.
- Approve retry limits and idempotency scope.
- Approve status and failure-retention display.

## 12. FHIR and ABDM Interoperability

### Proposal requirement

Use appropriate FHIR R4 concepts where applicable and consider applicable ABDM implementation guidance and consent-based exchange requirements.

### Data flow

Internal versioned record → validated mapping/profile layer → export or integration boundary → consent-aware exchange system.

### Dependencies

- FHIR R4 resource definitions
- Selected published implementation guide
- Terminology and identifier systems
- Consent model
- Tenant and hospital identifiers
- ABDM integration environment if approved

### Risks

- Unsupported profile assumptions.
- Identifier mismatch.
- Loss of source/verification metadata.
- Exchange before consent validation.
- Treating an MVP mapping as production-ready compliance.

### Alternatives

- Native FHIR persistence: improves interoperability but increases schema and search complexity.
- Internal relational model with FHIR mapping: more proportionate for an academic MVP.
- Direct ABDM integration: deferred unless the sandbox, credentials and scope are approved.

HL7 FHIR R4 defines resources such as Patient, Encounter, Condition, AllergyIntolerance, Observation, DiagnosticReport, DocumentReference, MedicationStatement and MedicationRequest. FHIR also defines security, Consent and AuditEvent-related concepts. [5]

ABDM provides published developer portal and implementation resources. No claim of ABDM compliance should be made until a selected guide, implementation scope and validation evidence exist. [6]

**Decision awaiting approval**

- Approve internal FHIR-compatible mapping versus native FHIR storage.
- Approve the specific ABDM guide, implementation scope and sandbox.
- Approve the MVP identifier and consent representation.

## 13. Testing, Deployment and Security Boundaries

### Testing

The proposal requires synthetic, difficult and normal scenarios. Tests should include:

- Wrong-patient and tenant isolation
- RBAC and object-level authorization
- Document extraction against original values
- Exact source navigation
- Transcript and speaker-attribution corrections
- Negation and conflict extraction
- Allergy, interaction, duplicate-medicine and missing-information checks
- Briefing retrieval precision and partial failures
- AI output unsupported statements and missed facts
- Audit and version history
- Consent and audio retention
- Failure continuation and idempotency

Fast successful drafts are not evidence of clinical quality. Report error rates, false warnings, missed warnings, unsupported statements and clinician correction effort.

### Deployment boundary

The academic MVP should use:

- Synthetic data only
- Non-production credentials
- Isolated network or local development environment
- Encrypted storage and transport
- Separate development and test environments
- Secrets outside source control
- Limited externally connected services
- No real patient or prescription use

No production clinical deployment, digital-signature service or regulatory certification should be assumed.

### Security boundary

The backend is the security boundary. Required controls include:

- Server-side authentication
- Tenant and patient relationship checks
- Least-privilege roles
- Object-level authorization
- Input and file validation
- Encrypted transport and storage
- Retention and deletion controls
- Audit logs
- Secret management
- Dependency and vulnerability review
- Rate limiting and upload limits
- Avoid sensitive clinical data in general logs

### Deployment alternatives

- Local Docker Compose or equivalent: simple academic MVP, but formalized only after implementation approval.
- Managed application and database services: simpler operations but requires cloud, cost and data-processing decisions.
- Single application plus worker: proportionate for MVP.
- Separate microservices: unnecessary unless workload, isolation or independent scaling is approved.

**Decision awaiting approval**

- Approve deployment environment and secrets model.
- Approve ASVS target level and security test scope.
- Approve infrastructure and operations provider.
- Approve whether external document, speech or AI providers are permitted for synthetic MVP testing.

## 14. Major Technology Decisions Awaiting Approval

| Decision | Recommendation for assessment | Alternatives | Approval needed |
|---|---|---|---|
| Frontend | React + Vite + TypeScript + Tailwind CSS | Angular, Vue, server-rendered framework | **USER-APPROVED FOR ACADEMIC MVP** |
| Backend | Python FastAPI modular monolith | Django REST Framework, Node.js | **USER-APPROVED FOR ACADEMIC MVP** |
| Database | PostgreSQL | FHIR-native server, document database | **USER-APPROVED FOR ACADEMIC MVP** |
| Background jobs | Durable queue plus worker | Embedded task queue, managed queue | Confirm technology and hosting |
| Object storage | Private encrypted object storage | Local encrypted volume for MVP | Confirm deployment and retention |
| Authentication | Hosted or approved academic identity integration | Local demonstration authentication | Confirm provider/model |
| Authorization | RBAC + tenant + patient relationship + purpose checks | Pure RBAC, ABAC | Confirm MVP policy |
| OCR | Hybrid selectable-text/OCR | Managed OCR, open-source OCR | Confirm provider and formats |
| Speech recognition | Candidate evaluated ASR | Managed ASR, local model | Confirm languages and provider |
| Diarization | Candidate evaluated diarization | No diarization in MVP, managed model | Confirm scope |
| Generative AI | Structured-output model for drafts only | Local model, hosted model, rule-only MVP | Confirm provider/model |
| Medicine catalogue | Small curated synthetic catalogue | Licensed catalogue | Confirm source and update |
| Interoperability | Internal FHIR-compatible model for MVP | Native FHIR server, no exchange MVP | Confirm guide and mapping |
| PDF generation | Controlled server-side generation | Template engines, managed service | Confirm or defer |

No material technology choice is finalized by this assessment.

## 15. Academic MVP Definition

The MVP should demonstrate one synthetic end-to-end workflow:

- Synthetic patient and doctor accounts
- Synthetic patient history and timeline
- Limited report upload and source-linked viewing
- Consent-aware audio or manual fallback
- Timestamped transcript and limited speaker attribution
- Structured consultation draft
- Limited medicine catalogue
- Selected deterministic safety checks
- Prescription draft requiring doctor approval
- Care-plan and follow-up records
- Backend RBAC and audit demonstration

The MVP should not claim real clinical deployment, external record exchange, production signatures, multilingual clinical validation, comprehensive medicine interactions or regulatory compliance.

## 16. Sources Consulted

Official and proposal sources:

1. **Original proposal:** `MediFlow_AI_Final_Checked.docx`
2. **Repository overview:** `README.md`
3. **Agent instructions:** `AGENTS.md`
4. **React:** <https://react.dev/learn>
5. **FastAPI:** <https://fastapi.tiangolo.com/>
6. **PostgreSQL:** <https://www.postgresql.org/docs/current/>
7. **HL7 FHIR R4:** <https://hl7.org/fhir/R4/>
8. **ABDM Developer Portal:** <https://docs.abdm.gov.in/>
9. **OWASP ASVS:** <https://asvs.owasp.org/>

FHIR and ABDM sources require a specific implementation profile and legal/regulatory review before any exchange is implemented. The assessment does not establish compliance.

## 17. Verification and Residual Risks

**Verified**

- Repository instructions and proposal context were inspected.
- README and proposal scope were reviewed.
- Git status was inspected and showed `AGENTS.md`, `README.md` and `MediFlow_AI_Final_Checked.docx` as untracked.
- No implementation files or application code were created.
- The assessment is documentation-only.

**Not verified**

- No technology versions were selected.
- No dependencies or databases were tested.
- No clinical model quality was evaluated.
- No security controls or authorization were implemented.
- No ABDM or FHIR profile was validated.
- No real clinical or regulatory suitability was established.

**Residual risks**

- Model accuracy and clinical safety remain unvalidated.
- Speech quality may vary by accent and setting.
- OCR quality may vary by document format.
- Medicine catalogue and safety-rule completeness may be insufficient.
- Draft approval and signing require explicit product decisions.
- Security and tenant isolation require implementation and testing.
