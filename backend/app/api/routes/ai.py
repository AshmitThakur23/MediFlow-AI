from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.dependencies import AuthorizationContext, require_patient_object_access, require_roles
from app.core.config import settings
from app.models.encounter import Encounter
from app.models.patient import Patient


router = APIRouter(prefix="/ai", tags=["AI clinical drafts"])


class ClinicalDraftRequest(BaseModel):
    patient_id: UUID
    encounter_id: UUID | None = None
    transcript: str = Field(min_length=1, max_length=30000)
    manual_text: str = Field(default="", max_length=30000)


class PrescriptionMedicineDraft(BaseModel):
    medicine_name: str
    strength: str | None = None
    dose: str | None = None
    route: str | None = None
    frequency: str | None = None
    duration: str | None = None
    quantity: str | None = None
    instructions: str | None = None
    source_uncertainty: str | None = None


class PrescriptionDraftOutput(BaseModel):
    medicines: list[PrescriptionMedicineDraft]
    advice: list[str]
    follow_up: str | None = None
    missing_prescription_information: list[str]


class ExtractedDraft(BaseModel):
    chief_complaint: str
    history_of_present_illness: str
    patient_reported_facts: list[str]
    doctor_questions: list[str]
    examination_findings: list[str]
    assessment: str
    plan: str
    missing_information: list[str]
    uncertainty: list[str]
    medication_candidates: list[str]
    prescription_draft: PrescriptionDraftOutput


class ClinicalDraftResponse(BaseModel):
    is_ai_draft: Literal[True] = True
    clinical_approval_required: Literal[True] = True
    draft: ExtractedDraft
    transcript_length: int


@router.post("/clinical-draft", response_model=ClinicalDraftResponse)
def create_clinical_draft(
    request: ClinicalDraftRequest,
    context: AuthorizationContext = Depends(require_roles("doctor")),
) -> ClinicalDraftResponse:
    require_patient_object_access(context, request.patient_id)
    patient = context.db.scalar(
        select(Patient).where(
            Patient.hospital_id == context.hospital_id,
            Patient.id == request.patient_id,
        )
    )
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")

    if request.encounter_id is not None:
        encounter = context.db.scalar(
            select(Encounter).where(
                Encounter.hospital_id == context.hospital_id,
                Encounter.id == request.encounter_id,
            )
        )
        if encounter is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Encounter not found")
        if encounter.patient_id != patient.id:
            raise HTTPException(status.HTTP_409_CONFLICT, "Encounter does not belong to this patient")

    if not settings.gemini_api_key:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "GEMINI_API_KEY is not configured",
        )

    prompt = f"""
You are a clinical documentation assistant for an academic synthetic-data system.
Never diagnose, prescribe, sign, approve, or create a confirmed clinical assessment.
Produce an editable draft only.
Separate patient-reported statements from doctor findings.
Preserve negation, uncertainty, duration, missing information and contradictions.
Do not invent medicines, doses, diagnoses or findings.
The patient is synthetic.
Build a reviewable prescription_draft only. Never make it a confirmed prescription.
For each medicine candidate, preserve only information supported by the transcript.
If a dose, route, frequency or duration is missing or unclear, set it to null or
place it in missing_prescription_information. Do not invent clinical data.

Patient:
{patient.given_name} {patient.family_name}
MRN: {patient.synthetic_mrn}

Consultation transcript:
{request.transcript}

Clinician-entered text and existing template fields:
{request.manual_text or "None"}

Return only JSON matching the requested schema.
"""

    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        result = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
                response_schema=ExtractedDraft,
            ),
        )
        payload = ExtractedDraft.model_validate_json(result.text)
    except Exception as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Gemini could not generate a valid clinical draft",
        ) from exc

    return ClinicalDraftResponse(
        draft=payload,
        transcript_length=len(request.transcript),
    )
