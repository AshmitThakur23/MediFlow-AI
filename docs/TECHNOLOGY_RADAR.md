# MediFlow AI — Technology Radar

**Status:** Initial technology evaluation record

**Scope:** This radar records technologies mentioned or evaluated by the repository and proposal. Mentioning or recording a technology does not mean it has been technically validated, licensed, benchmarked or approved for implementation.

## Radar Legend

- **Approved:** Explicitly approved for the academic MVP.
- **Under evaluation / undecided:** Identified as a candidate but not technically validated or selected.
- **Not yet evaluated:** Relevant technology category or future need identified, but no candidate evaluation has been documented.
- **Rejected:** No current technology is recorded as rejected by the repository.

## Approved for Academic MVP

| Technology | Status | Scope and evidence |
| --- | --- | --- |
| React | **Approved** | Frontend component architecture; approved with Vite, TypeScript and Tailwind CSS. |
| Vite | **Approved** | Frontend build and development workflow. |
| TypeScript | **Approved** | Typed frontend implementation and API contracts. |
| Tailwind CSS | **Approved** | Frontend styling foundation. |
| Python | **Approved** | Backend and AI/document-processing implementation language. |
| FastAPI | **Approved** | Backend API and workflow framework. |
| PostgreSQL | **Approved** | Primary structured database for synthetic academic MVP data. |
| PBKDF2-HMAC-SHA256 | **Approved for academic MVP** | Local synthetic-account password hashing using random 16-byte salts and 600,000 iterations. |
| HTTP Basic with HTTPS | **Under evaluation** | Current academic-MVP credential transport boundary; production token/session and HTTPS requirements remain unverified. |

These approvals are limited to the academic MVP. Exact versions, production infrastructure and runtime compatibility remain undetermined.

## Under Evaluation / Undecided

| Technology or category | Status | Proposed role | Validation still required |
| --- | --- | --- | --- |
| Redis | **Under evaluation** | Possible cache, queue broker or transient state support | Deployment, licensing, persistence, data model, compatibility and security |
| Managed OCR | **Under evaluation** | Cloud document text extraction | Privacy, accuracy, licensing, cost, retention and synthetic-data suitability |
| Open-source OCR | **Under evaluation** | Local or self-hosted document extraction | Runtime compatibility, licensing, accuracy, packaging and maintenance |
| Hybrid OCR pipeline | **Under evaluation** | Prefer selectable PDF text, then OCR and human verification | Quality, page references, bounding boxes and failure behavior |
| Managed ASR | **Under evaluation** | Consultation speech recognition | Accuracy, privacy, pricing, language support and retention |
| Whisper or another ASR model | **Under evaluation** | Local or hosted speech recognition candidate | License, runtime, clinical terminology, accent and code-switching evaluation |
| Managed diarization | **Under evaluation** | Speaker turn attribution | Accuracy, privacy, licensing and confidence reporting |
| pyannote.audio or another diarization model | **Under evaluation** | Open or managed speaker-attribution candidate | License, runtime, speaker accuracy and confidence metadata |
| Hosted structured-output LLM | **Under evaluation** | Clinical extraction and draft generation | Privacy, licensing, model version, prompt stability and clinical-quality evaluation |
| Local open or hosted open model | **Under evaluation** | Data-controlled structured extraction or draft candidate | Licensing, hardware, quality, provenance and security |
| LLM provider alternatives | **Under evaluation** | Generative clinical extraction and summarization | Vendor terms, data handling, model versions and evaluation evidence |
| Browser MediaRecorder | **Under evaluation** | Proposed academic audio capture mechanism | Browser support, transport security, consent and retention |
| Private object storage | **Under evaluation** | Original documents and recordings | Encryption, retention, access, backup and provider choice |
| Background job queue | **Under evaluation** | Asynchronous OCR, transcription and briefing jobs | Durability, retry, idempotency, hosting and tenant isolation |
| Authentication provider or academic local identity | **Under evaluation** | Synthetic doctor, patient and pharmacy identities | Security, token handling, audit attribution and production readiness |
| PDF generation service or library | **Under evaluation** | Controlled approved-document output | Template security, dependencies, licensing and signing integration |
| Curated medicine catalogue | **Under evaluation** | Generic and brand medicine lookup | Source quality, licensing, update process and safety coverage |
| FHIR R4 | **Under evaluation** | Interoperability resources and mapping | Applicable profiles, identifiers, terminology and validation |
| ABDM | **Under evaluation** | Future consent-based health-information exchange | Published implementation guide, sandbox, consent model and compliance scope |
| OWASP ASVS | **Under evaluation** | Security verification framework | Target level and evidence scope |

Redis is undecided and is not approved. No Redis functionality should be considered implemented or production-ready based on this radar entry alone.

No OCR, ASR, diarization or LLM provider is approved by this radar. The presence of Whisper, pyannote.audio or another provider name is a record of proposal or architecture categories, not technical validation.

## Not Yet Evaluated

The following categories or choices are identified by the proposal but have not yet been evaluated with named candidates or evidence:

| Area | Status | Needed evaluation |
| --- | --- | --- |
| Cloud or production hosting | **Not yet evaluated** | Region, cost, tenancy, backup, recovery and data residency |
| Production digital-signature infrastructure | **Not yet evaluated** | Authorized signing mechanism, key management and workflow |
| India EHR Standards 2016 implementation mapping | **Not yet evaluated** | Applicable published requirements and implementation evidence |
| DPDP Act and Rules implementation mapping | **Not yet evaluated** | Applicability, commencement, lawful processing and retention obligations |
| Clinical terminology and coding | **Not yet evaluated** | Terminology scope, mappings and maintenance |
| Medicine interaction and dosing engine | **Not yet evaluated** | Data source, rules, validation and update process |
| Production monitoring and observability | **Not yet evaluated** | Logs, metrics, traces, alerting and clinical-data redaction |
| Automated accessibility testing | **Not yet evaluated** | Target standard, browser coverage and clinical workflow usability |
| Deployment orchestration | **Not yet evaluated** | Local MVP and managed deployment alternatives |
| Disaster recovery and backup | **Not yet evaluated** | Recovery objectives, restoration tests and media retention |

## Rejected

No technology is recorded as rejected at this stage.

## Evaluation Requirements

A technology must not move to Approved until the repository records:

- Its responsibility and integration boundary.
- Alternatives considered.
- License and dependency findings.
- Security and privacy considerations.
- Compatibility with the approved React/Vite/TypeScript/Tailwind, Python/FastAPI and PostgreSQL stack.
- Evidence relevant to the academic MVP.
- Adoption or rejection rationale in `TECHNOLOGY_DECISIONS.md`.
- Exact versions and compatibility only after a version evaluation is requested and documented.

## Sources and Existing Repository Evidence

- `MediFlow_AI_Final_Checked.docx`: original proposal and proposed technology directions.
- `README.md`: approved repository overview and proposed architecture.
- `AGENTS.md`: permanent evaluation and adoption policy.
- `docs/ARCHITECTURE_ASSESSMENT.md`: initial component, risk and alternative assessment.
- `docs/TECHNOLOGY_DECISIONS.md`: the three core academic MVP approval records.
