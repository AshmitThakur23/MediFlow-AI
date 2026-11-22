from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import AuthorizationContext, require_patient_object_access, require_roles
from app.models.clinical_note_draft import ClinicalNoteDraft
from app.models.encounter import Encounter
from app.models.patient import Patient


router = APIRouter(prefix="/clinical-notes", tags=["clinical notes"])


class ClinicalTemplateRequest(BaseModel):
    patient_id: UUID
    encounter_id: UUID
    transcript_text: str = Field(min_length=1, max_length=30000)
    chief_complaint: str = Field(min_length=1, max_length=255)
    history: str = ""
    patient_facts: str = ""
    doctor_questions: str = ""
    examination_findings: str = ""
    assessment: str = ""
    plan: str = ""
    missing_information: str = ""


class ClinicalTemplateApprovalRequest(BaseModel):
    approved: bool


class ClinicalTemplateResponse(BaseModel):
    id: UUID
    hospital_id: UUID
    patient_id: UUID
    encounter_id: UUID
    created_by_hospital_user_id: UUID
    transcript_text: str
    chief_complaint: str
    history: str
    patient_facts: str
    doctor_questions: str
    examination_findings: str
    assessment: str
    plan: str
    missing_information: str
    status: str
    created_at: datetime
    updated_at: datetime


def validate_patient_encounter(
    context: AuthorizationContext,
    patient_id: UUID,
    encounter_id: UUID,
) -> None:
    require_patient_object_access(context, patient_id)
    patient = context.db.scalar(
        select(Patient).where(
            Patient.hospital_id == context.hospital_id,
            Patient.id == patient_id,
        )
    )
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    encounter = context.db.scalar(
        select(Encounter).where(
            Encounter.hospital_id == context.hospital_id,
            Encounter.id == encounter_id,
        )
    )
    if encounter is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Encounter not found")
    if encounter.patient_id != patient_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Encounter does not belong to the patient",
        )


@router.post("/drafts", response_model=ClinicalTemplateResponse, status_code=201)
def save_clinical_template(
    request: ClinicalTemplateRequest,
    context: AuthorizationContext = Depends(require_roles("doctor")),
) -> ClinicalTemplateResponse:
    validate_patient_encounter(context, request.patient_id, request.encounter_id)
    draft = ClinicalNoteDraft(
        hospital_id=context.hospital_id,
        patient_id=request.patient_id,
        encounter_id=request.encounter_id,
        created_by_hospital_user_id=context.assignment.id,
        transcript_text=request.transcript_text,
        chief_complaint=request.chief_complaint,
        history=request.history,
        patient_facts=request.patient_facts,
        doctor_questions=request.doctor_questions,
        examination_findings=request.examination_findings,
        assessment=request.assessment,
        plan=request.plan,
        missing_information=request.missing_information,
        status="draft",
    )
    context.db.add(draft)
    try:
        context.db.commit()
    except IntegrityError as exc:
        context.db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Clinical note draft integrity was rejected",
        ) from exc
    context.db.refresh(draft)
    return ClinicalTemplateResponse.model_validate(draft, from_attributes=True)


@router.get("/drafts", response_model=list[ClinicalTemplateResponse])
def list_clinical_templates(
    patient_id: UUID,
    context: AuthorizationContext = Depends(require_roles("doctor")),
) -> list[ClinicalTemplateResponse]:
    require_patient_object_access(context, patient_id)
    rows = context.db.scalars(
        select(ClinicalNoteDraft).where(
            ClinicalNoteDraft.hospital_id == context.hospital_id,
            ClinicalNoteDraft.patient_id == patient_id,
        ).order_by(ClinicalNoteDraft.created_at.desc())
    ).all()
    return [
        ClinicalTemplateResponse.model_validate(row, from_attributes=True)
        for row in rows
    ]


@router.patch("/drafts/{draft_id}/approval", response_model=ClinicalTemplateResponse)
def approve_clinical_template(
    draft_id: UUID,
    request: ClinicalTemplateApprovalRequest,
    context: AuthorizationContext = Depends(require_roles("doctor")),
) -> ClinicalTemplateResponse:
    draft = context.db.scalar(
        select(ClinicalNoteDraft).where(
            ClinicalNoteDraft.hospital_id == context.hospital_id,
            ClinicalNoteDraft.id == draft_id,
        )
    )
    if draft is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clinical note draft not found")
    require_patient_object_access(context, draft.patient_id)
    if draft.status != "draft":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Only an existing draft can be approved or cancelled",
        )
    draft.status = "approved" if request.approved else "cancelled"
    context.db.commit()
    context.db.refresh(draft)
    return ClinicalTemplateResponse.model_validate(draft, from_attributes=True)
