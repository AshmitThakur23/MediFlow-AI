# MediFlow AI — Technology Decisions

**Status:** Academic MVP technology decisions record

**Scope:** This document records the core technologies explicitly approved by the user for the MediFlow AI academic MVP. It does not approve a production architecture, dependency versions, hosting model or clinical deployment.

## Decision Summary

| Technology decision | Approval status | Scope |
| --- | --- | --- |
| React + Vite + TypeScript + Tailwind CSS | **USER-APPROVED FOR ACADEMIC MVP** | Frontend foundation |
| Python + FastAPI | **USER-APPROVED FOR ACADEMIC MVP** | Backend API and workflow foundation |
| PostgreSQL | **USER-APPROVED FOR ACADEMIC MVP** | Primary structured database |
| Synthetic local identity with PBKDF2-HMAC-SHA256 passwords | **USER-APPROVED FOR ACADEMIC MVP** | Academic local-account authentication |

No exact dependency or runtime versions are selected in this record.

## TD-001: React + Vite + TypeScript + Tailwind CSS

**Approval status:** USER-APPROVED FOR ACADEMIC MVP

**Decision:** Use React with Vite, TypeScript and Tailwind CSS for the MediFlow AI academic MVP frontend.

**Responsibility:**

- Render the doctor queue and Call Next Patient workflow.
- Render source-linked patient briefings and preparation states.
- Provide the consent-aware consultation room and manual documentation fallback.
- Provide clinical-note, prescription and care-plan review interfaces.
- Display separate AI draft and clinician-approved states.
- Provide the minimum-necessary pharmacy dispensing view.
- Link findings to original reports and timeline records.

**Selection rationale:**

- React supports component-based implementation of the doctor, patient and pharmacy interfaces.
- Vite provides an academic frontend build and development workflow.
- TypeScript adds static type information for API contracts and UI state.
- Tailwind CSS provides a configurable styling foundation for a consistent interface.
- The combination aligns with the proposed technology direction in the MediFlow AI proposal and README.
- Backend authorization remains mandatory; the frontend is not a security boundary.

**Alternatives considered:**

- React with JavaScript instead of TypeScript: simpler initially, but weaker type coverage for clinical data and API shapes.
- Server-rendered frameworks: potentially suitable, but less aligned with the proposal's component-oriented frontend direction.
- Vue or Angular: viable frontend alternatives, but not approved for this MVP.
- Using a component library or design system: not yet selected and may require separate evaluation.

**Risks and unresolved questions:**

- Browser audio support and secure capture behavior require evaluation.
- PDF and image navigation require a suitable viewer integration.
- Frontend state must distinguish proposed, draft and approved records clearly.
- A UI framework choice does not validate accessibility, security or clinical usability.

**Production boundary:** This approval does not finalize React, Vite, TypeScript or Tailwind CSS versions, deployment approach, browser support policy or production frontend architecture.

## TD-002: Python + FastAPI

**Approval status:** USER-APPROVED FOR ACADEMIC MVP

**Decision:** Use Python with FastAPI for the MediFlow AI academic MVP backend.

**Responsibility:**

- Expose typed APIs for identity, queue, patients, encounters and clinical timeline records.
- Implement backend authentication and role, tenant, relationship and purpose authorization.
- Orchestrate document, audio, transcript, AI, approval and pharmacy workflows.
- Submit and reconcile versioned clinical records.
- Start and monitor background jobs.
- Record audit events and preserve source and verification metadata.
- Keep AI-generated notes and prescriptions as drafts until clinician approval.

**Selection rationale:**

- Python is compatible with the proposal's document-processing, speech, generative-AI and clinical-safety components.
- FastAPI provides typed Python APIs and OpenAPI-based API documentation.
- The modular monolith is proportionate for an academic MVP and avoids unnecessary microservice decomposition.
- FastAPI supports an API-first implementation that can be separated from the frontend and worker services.

**Alternatives considered:**

- Django REST Framework: a valid Python alternative with more built-in framework conventions, but not selected.
- Node.js: viable for web APIs, but less aligned with the proposal's Python-oriented processing stack.
- Go or Java: viable service alternatives, but not approved for this MVP.
- Microservices: not approved and likely unnecessary for the initial academic scope.

**Risks and unresolved questions:**

- Backend authorization must be enforced independently of frontend behavior.
- Synchronous AI or document calls must not block queue workflows.
- Approval endpoints require explicit clinician authorization and audit controls.
- Background jobs need durable state, retries and idempotency.
- Python runtime, framework and dependency versions remain to be evaluated and documented.

**Production boundary:** This approval establishes the academic MVP technology direction only. It does not approve a production deployment model, service topology, runtime versions, scaling design or regulatory controls.

## TD-003: PostgreSQL

**Approval status:** USER-APPROVED FOR ACADEMIC MVP

**Decision:** Use PostgreSQL as the primary structured database for the MediFlow AI academic MVP.

**Responsibility:**

- Store synthetic patient and encounter data.
- Store conditions, allergies, medication statements and medication requests.
- Store observations and diagnostic-report metadata.
- Store document references, transcript segments and consent metadata.
- Store clinical notes, care plans and care instructions.
- Preserve approval, correction, source, verification and status information.
- Store version history and audit events.
- Enforce tenant, patient, encounter and referential relationships.

**Selection rationale:**

- PostgreSQL is a relational database suitable for structured clinical records and audit requirements.
- Relational constraints can support referential integrity and wrong-patient controls.
- It is compatible with source-of-truth modeling for synthetic academic data.
- It supports transactional persistence for versions and approval state.
- It is compatible with FHIR-aligned internal mappings without requiring native FHIR persistence in the MVP.

**Alternatives considered:**

- A native FHIR server: better for standards-based resource exchange but adds profiling and implementation-guide complexity.
- A document database: flexible for varied documents, but weaker for relational integrity and object-level authorization.
- A relational database family other than PostgreSQL: not approved for this MVP.
- PostgreSQL plus an external FHIR mapping layer: remains a future evaluation, not a final production choice.

**Risks and unresolved questions:**

- FHIR mapping and identifier strategy require approval.
- Audit retention and table partitioning need later review.
- Encryption, backup and recovery configuration remain unapproved.
- Object storage is still required for original documents and recordings.
- Database version, migrations and operational tooling are not selected.

**Production boundary:** PostgreSQL approval is limited to the academic MVP. It does not approve production hosting, replication, backup, disaster recovery, encryption configuration or a clinical data-governance architecture.

## TD-004: Synthetic Local Identity with PBKDF2 Password Hashing

**Approval status:** USER-APPROVED FOR ACADEMIC MVP

**Decision:** Use synthetic local user accounts for the academic MVP, with
PBKDF2-HMAC-SHA256 password hashes, random salts, and 600,000 iterations.
Use HTTP Basic credentials for the first API boundary only.

**Responsibility:**

- Authenticate synthetic doctors and other academic-MVP accounts.
- Reject disabled users and incorrect passwords.
- Associate an authenticated user with active, currently valid
  hospital-user assignments.
- Verify that a requested hospital has an active assignment.
- Preserve the separation between global `User` identity and
  hospital-specific `HospitalUser` assignments.

**Selection rationale:**

- The implementation uses standard-library cryptographic primitives and does
  not require an additional password-hashing dependency.
- Random salts prevent identical passwords from producing identical hashes.
- Constant-time digest comparison reduces timing comparison leakage.
- The existing `User` and `HospitalUser` models support a local academic
  identity and tenant-assignment boundary.

**Alternatives considered:**

- External identity provider: stronger production capability, but provider,
  audience, issuance and deployment choices remain unapproved.
- JWT or opaque bearer session: useful for later API work, but requires a
  token format, expiration, secret, revocation and storage decision.
- HTTP Basic: adequate only with enforced HTTPS and local synthetic testing;
  it is not a final production session or federation design.

**Risks and unresolved questions:**

- The 600,000-iteration cost may require performance benchmarking.
- Password reset, account lockout, MFA and recovery workflows are not implemented.
- HTTP Basic credentials must only be used over protected transport.
- Role and permission enforcement remains incomplete.
- Production secret management, token revocation and session policies remain
  undecided.

**Production boundary:** This decision is limited to synthetic academic-MVP
authentication. It does not approve production identity, HTTPS configuration,
password recovery, session management, MFA or clinical deployment.

## Cross-Decision Constraints

The approved core technologies must support these proposal requirements:

- Synthetic academic data only.
- Source, date, author and verification status on clinical facts.
- Versioned corrections rather than silent overwrites.
- Backend tenant and patient relationship isolation.
- Clinician review and approval for notes, prescriptions and care plans.
- AI outputs remain drafts.
- Asynchronous processing must not block the queue or manual workflow.
- Audit records for access, edits, approvals, exports, signing and sharing.

## Decisions Not Approved

The following areas remain undecided or require further evaluation:

- Exact framework, library or runtime versions.
- Redis or another cache/job technology.
- OCR provider or open-source OCR engine.
- Speech recognition and diarization providers.
- Generative AI or local model provider.
- Medicine catalogue source.
- Authentication provider.
- Object-storage provider.
- Job queue provider.
- PDF generation service.
- Cloud or production deployment platform.
- Native FHIR persistence versus internal FHIR-compatible mapping.
- ABDM implementation guide and sandbox scope.

Production architecture and clinical readiness are not approved by these academic MVP decisions.
