# MediFlow AI — Agent Instructions

These instructions are permanent for every AI coding agent, including GitHub Copilot. They supplement repository documentation and Git history.

## 1. Project Identity and Purpose

MediFlow AI is a proposed AI-assisted clinical workflow platform for healthcare professionals. It is intended to connect available patient history, the current consultation and future care while preserving source evidence and clinician control.

The project helps doctors find relevant historical information, document consented consultations, prepare editable clinical-note drafts, support medicine and prescription review, and organize patient-care instructions and follow-up. The system supports qualified healthcare professionals and must not replace their clinical judgment.

No feature is considered implemented unless it exists in the repository and is verified with evidence.

## 2. Original MediFlow AI Proposal

The original MediFlow AI project proposal stored in this repository as `MediFlow_AI_Final_Checked.docx` is the primary functional specification.

Agents must preserve the proposal's intended functionality, terminology and boundaries. Use the proposal for:

- Product purpose and objectives
- The nine clinical modules
- End-to-end doctor, patient and pharmacy workflows
- Clinical memory and source-linking requirements
- Consent, privacy and safety requirements
- Academic MVP scope and future production scope
- Testing and acceptance criteria

Do not invent requirements, materially change proposal functionality or present proposed features as implemented. If the proposal conflicts with repository documentation, stop and report the conflict rather than silently choosing a different interpretation.

## Conflict Resolution

If the proposal, `README.md`, architecture documents or implementation evidence conflict, stop and report the exact conflict with file references. Do not independently change the product requirements or choose a resolution based on assumption. Ask the user to resolve material product or architecture conflicts.

## 3. README.md as Approved Product Overview

`README.md` is the approved repository-level product overview and persistent project description. It must remain consistent with the original proposal and with implemented repository state.

When documentation and code differ, inspect the relevant evidence, tests and Git history before proceeding. Update `README.md` when the approved overview changes as a result of an actual completed task.

## 4. Documentation-Reading Rules

Before starting every task:

1. Read `README.md`.
2. Read this `AGENTS.md`.
3. Read applicable repository instructions and Copilot instruction files.
4. Read `CURRENT_TASK.md` when it exists.
5. Read relevant architecture, design and dependency documentation when it exists.
6. Inspect the relevant source files, tests and Git status.
7. Reconstruct the task scope and constraints from evidence before making changes.

Once files such as `CURRENT_TASK.md`, `TECHNOLOGY_RADAR.md`, `TECHNOLOGY_DECISIONS.md` or ADR documents exist, they must be treated as required task context when relevant.

Do not begin implementation solely from conversation history or assumptions.

## 5. Context Recovery Rules

Never rely exclusively on AI conversation memory or the current context window.

If context is lost, interrupted or uncertain:

1. Re-read repository Markdown documentation.
2. Inspect Git status, branches, tracked files, diffs and relevant commit history.
3. Inspect source, configuration and tests for the actual repository state.
4. Reconstruct the current task, completed work and verification evidence.
5. Identify contradictions or missing information explicitly.
6. Do not continue a task until the project state is supported by repository evidence.

Historical development records must be preserved. Git history is a recovery source, not a reason to rewrite existing history.

## 6. Architecture and Technology Decisions

New or changed architecture and technology decisions require explicit analysis and documentation.

Before adopting technology:

- Research the proposal-relevant requirements and official evidence.
- Evaluate correctness, security, privacy, licensing, maintainability and compatibility.
- Compare alternatives when a decision is material.
- Record the decision and rationale in `TECHNOLOGY_DECISIONS.md`.
- Record every newly evaluated technology in `TECHNOLOGY_RADAR.md`.
- Create an Architecture Decision Record where appropriate.
- Clearly distinguish proposed architecture from implemented architecture.

Do not make architectural technology choices only because they appear convenient or are mentioned by an AI model. Do not claim an adopted or rejected decision is final without repository documentation.

### Model Selection and Engineering Quality

When available in the IDE, use a strong Claude or ChatGPT model for complex architecture, security, clinical-safety, database-design and code-review tasks. Lightweight models may be used for simple mechanical tasks.

Never claim that a model was selected automatically. Model selection is controlled by the user.

## 7. Clinical Data Integrity and Persistent Memory

The system must preserve longitudinal clinical information with source, date, author and verification status.

Rules include:

- Keep dated records from consultations, reports, prescriptions, admissions and instructions.
- Distinguish confirmed information, patient-reported information, imported records, clinician observations and AI-generated drafts.
- Preserve old records and approved clinical facts.
- Never silently overwrite or delete a historical clinical record.
- Use versioned corrections or additional dated timeline entries.
- Reconcile conflicting facts without hiding them until authorized review.
- Carefully perform duplicate-patient matching to avoid mixing records.
- Distinguish current medication statements from historical prescriptions and patient-reported use.
- Preserve source-document identity, page references and uncertainty.
- Treat missing information as unknown, not as a negative finding.

AI summaries and vector-search results must not replace structured, verified clinical records.

## 8. Patient Privacy, Tenant Isolation and RBAC

Clinical data access must use defense-in-depth and backend authorization.

Agents must implement or document controls based on:

- Role
- Hospital or tenant
- Patient relationship
- Legitimate purpose
- Least-privilege access

Never expose patient information across unauthorized hospital tenants or unrelated patient records. Frontend visibility is not a security boundary.

Apply consent, retention, encryption, audit, export and restricted-note requirements. Record views, edits, approvals, exports, sharing, signing and dispensing where relevant.

Pharmacy access must remain limited to the approved prescription and the minimum necessary dispensing and safety information. Restricted clinician notes, complete histories, unrelated reports and consultation transcripts must not be exposed automatically.

## 9. Clinical AI Safety and Human Approval

AI must never independently:

- Diagnose
- Prescribe
- Sign a prescription or clinical document
- Approve treatment
- Assign an unsupported Critical clinical label
- Make an irreversible clinical decision

Every AI-generated summary, extraction, warning, medicine suggestion, transcript interpretation, prescription draft or care-plan draft remains a draft until reviewed and authorized by the appropriate healthcare professional.

Clinical safety requires:

- Source-linked evidence
- Provenance and verification status
- Deterministic, validated and versioned safety rules
- Explicit uncertainty
- Negation and conflict handling
- Human correction and approval
- Manual documentation fallback
- No fabrication of missing records or clinical findings

LLMs must not invent medicines, doses, diagnoses or clinical rules.

## 10. Coding Standards and Modularity

Write only code requested or necessary for the approved task.

Use existing repository conventions and patterns. Keep modules cohesive and interfaces explicit. Prefer small, testable components over unrelated refactoring.

Coding work must preserve:

- Type safety
- Input validation
- Error handling
- Least-privilege authorization
- Auditability
- Privacy and data minimization
- Existing behavior unless a documented requirement changes it

Do not add dependencies without an approved dependency change and compatibility review. Do not create application code, folders or files outside an approved task scope.

## 11. Testing and Verification Requirements

Every task requires evidence appropriate to the change.

Testing must cover relevant behavior and risk, including:

- Functional output
- Wrong-patient and tenant isolation
- Permission boundaries
- Clinical draft versus approved-record boundaries
- Partial and failed processing
- Audit history
- Data provenance
- Relevant edge cases

Do not claim a feature or test passed without observable evidence such as command output, test results or source verification. If evidence is unavailable, state that verification is incomplete.

Never proceed to the next task when the current task has failed verification.

Verification evidence must match the task type:

- **Documentation-only:** inspect the complete changed content and the Git diff.
- **Code changes:** run the relevant automated tests and inspect the diff.
- **Configuration/dependency changes:** validate configuration, exact versions and compatibility.
- **Security-sensitive changes:** perform the relevant security and authorization checks.

Never claim tests passed without actual output from the verification run.

## 12. Documentation Update Requirements

After every successful task, update the appropriate repository Markdown documentation with actual changes and verification evidence.

Documentation updates must:

- Describe what changed
- Preserve historical development context
- Distinguish proposed functionality from implemented functionality
- Record test commands and actual results
- Reference relevant files or sections
- Avoid unsupported claims

Append dated entries to development records where appropriate. Never rewrite or silently erase historical project records.

## 13. Technology Evaluation and Dependency Management

Before evaluating or adopting a technology:

- Research official and reliable sources.
- Record evaluation in `TECHNOLOGY_RADAR.md`.
- Record adopted or rejected architectural rationale in `TECHNOLOGY_DECISIONS.md`.
- Create an ADR where the decision is architectural and material.

For dependencies:

- Preserve exact versions
- Record licensing
- Assess security concerns
- Check runtime and platform compatibility
- Review transitive dependencies
- Document upgrade and rollback considerations

Do not add a dependency unless it is necessary for an approved task and the repository decision process supports it.

## 14. Git Branch, Commit and Rollback Rules

Work within the repository root unless the user explicitly requires otherwise.

Before destructive or history-changing actions:

- Inspect `git status`
- Inspect branches and diffs
- Preserve user and repository changes
- Do not reset, rebase or rewrite history without explicit authorization
- Do not force-push
- Do not delete branches or files without explicit authorization

Do not stage or commit unless the task explicitly requests it.

Do not invent a co-author identity or trailer. Before adding a co-author trailer to a commit, use only an explicitly approved identity and exact format. If no co-author identity and exact format have been approved, ask the user or omit the trailer.

Branch names and commits must not overwrite existing development records.

Rollback must prefer targeted, reviewable operations and must not discard unrelated work.

## 15. Task-by-Task Development Workflow

Use this workflow for every task:

1. Read project documentation and applicable instructions.
2. Inspect repository status and relevant files.
3. Restate the scope and acceptance criteria.
4. Identify dependencies and constraints.
5. Make only requested, complete and relevant changes.
6. Run the smallest evidence-producing verification.
7. Inspect the resulting diff or file output.
8. Update relevant documentation.
9. Report exact changes, verification evidence and any remaining issues.
10. Stop after the task unless an explicitly requested follow-on task remains.

Do not mix unrelated work into a task.

## 16. Prohibition on Unverified Claims

Never claim:

- A feature exists
- A feature was implemented
- A test passed
- A vulnerability is absent
- A standard or legal requirement is satisfied
- A deployment or integration succeeded

unless repository evidence, test evidence or explicit task instructions support the claim.

Use wording such as "proposed", "not implemented", "verification incomplete" or "verified by..." instead of unsupported certainty.

## 17. Handling Incomplete Tasks and Failures

If a task cannot be completed or verification fails:

1. Stop current implementation where continuing would compound risk.
2. Preserve any existing or newly made work safely.
3. Identify the exact blocker or failed check.
4. Report relevant command output or evidence.
5. Do not present the task as successful.
6. Do not proceed to an unrelated next task.
7. Request clarification only when user input is needed to resolve the blocker.

If a partial implementation is unavoidable, clearly separate completed work from unverified or missing work. Never use success-shaped fallback language.

## Permanent Rules Summary

- Never rely exclusively on AI conversation memory.
- Always reconstruct current project state from repository documentation and Git history.
- Read `CURRENT_TASK.md` and relevant project documentation before each task, once those files exist.
- Never silently overwrite historical clinical records.
- Never expose patient information across unauthorized hospital tenants.
- Never let AI independently diagnose, prescribe, sign or approve clinical decisions.
- Every AI-generated clinical output remains a draft until authorized clinician approval.
- Every task requires evidence, tests and a detailed report.
- Update relevant Markdown documentation after successful tasks.
- New technology must be researched, evaluated and documented before adoption.
- Do not make unrelated modifications.
- Never proceed to the next task when the current task has failed verification.
