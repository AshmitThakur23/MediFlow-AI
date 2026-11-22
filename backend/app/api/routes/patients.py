from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import (
    AuthorizationContext,
    require_patient_object_access,
    require_roles,
)
from app.models.appointment import Appointment
from app.models.allergy_intolerance import AllergyIntolerance
from app.models.condition import Condition
from app.models.encounter import Encounter
from app.models.medication_statement import MedicationStatement
from app.models.observation import Observation
from app.models.patient import Patient


router = APIRouter(prefix="/patients", tags=["patients"])


class PatientCreateRequest(BaseModel):
    synthetic_mrn: str = Field(min_length=1, max_length=64)
    given_name: str = Field(min_length=1, max_length=128)
    family_name: str = Field(min_length=1, max_length=128)
    date_of_birth: date
    sex_at_birth: str | None = Field(default=None, max_length=24)
    identity_status: str = "unverified"


class PatientResponse(BaseModel):
    id: UUID
    hospital_id: UUID
    synthetic_mrn: str
    given_name: str
    family_name: str
    date_of_birth: date
    sex_at_birth: str | None
    identity_status: str
    merged_into_patient_id: UUID | None


class PatientTimelineItemResponse(BaseModel):
    item_type: str
    id: UUID
    status: str
    at: date | None = None


@router.post(
    "",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_patient(
    request: PatientCreateRequest,
    context: AuthorizationContext = Depends(require_roles("doctor", "staff")),
) -> PatientResponse:
    if request.identity_status not in {
        "verified",
        "probable",
        "unverified",
        "merged",
    }:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid patient identity status",
        )
    patient = Patient(
        hospital_id=context.hospital_id,
        synthetic_mrn=request.synthetic_mrn,
        given_name=request.given_name,
        family_name=request.family_name,
        date_of_birth=request.date_of_birth,
        sex_at_birth=request.sex_at_birth,
        identity_status=request.identity_status,
    )
    context.db.add(patient)
    try:
        context.db.commit()
    except IntegrityError as exc:
        context.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Patient could not be created",
        ) from exc
    context.db.refresh(patient)
    return to_patient_response(patient)


@router.get("", response_model=list[PatientResponse])
def search_patients(
    q: str | None = Query(default=None, min_length=1, max_length=128),
    limit: int = Query(default=25, ge=1, le=100),
    context: AuthorizationContext = Depends(
        require_roles("doctor", "staff", "pharmacist")
    ),
) -> list[PatientResponse]:
    if context.assignment.relationship_scope != "hospital":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient search requires hospital relationship scope",
        )
    statement = select(Patient).where(
        Patient.hospital_id == context.hospital_id,
        Patient.merged_into_patient_id.is_(None),
    )
    if q:
        pattern = f"%{q}%"
        statement = statement.where(
            (Patient.synthetic_mrn.ilike(pattern))
            | (Patient.given_name.ilike(pattern))
            | (Patient.family_name.ilike(pattern))
        )
    statement = statement.limit(limit)
    patients = context.db.scalars(statement).all()
    return [to_patient_response(patient) for patient in patients]


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: UUID,
    context: AuthorizationContext = Depends(
        require_roles("doctor", "staff", "pharmacist")
    ),
) -> PatientResponse:
    require_patient_object_access(context, patient_id)
    patient = context.db.scalar(
        select(Patient).where(
            Patient.hospital_id == context.hospital_id,
            Patient.id == patient_id,
        )
    )
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    return to_patient_response(patient)


@router.get("/{patient_id}/timeline")
def get_patient_timeline(
    patient_id: UUID,
    context: AuthorizationContext = Depends(require_roles("doctor", "staff")),
) -> list[PatientTimelineItemResponse]:
    require_patient_object_access(context, patient_id)
    patient = context.db.scalar(
        select(Patient).where(
            Patient.hospital_id == context.hospital_id,
            Patient.id == patient_id,
        )
    )
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    appointments = context.db.scalars(
        select(Appointment).where(
            Appointment.hospital_id == context.hospital_id,
            Appointment.patient_id == patient_id,
        )
    ).all()
    encounters = context.db.scalars(
        select(Encounter).where(
            Encounter.hospital_id == context.hospital_id,
            Encounter.patient_id == patient_id,
        )
    ).all()
    conditions = context.db.scalars(
        select(Condition).where(
            Condition.hospital_id == context.hospital_id,
            Condition.patient_id == patient_id,
        )
    ).all()
    allergies = context.db.scalars(
        select(AllergyIntolerance).where(
            AllergyIntolerance.hospital_id == context.hospital_id,
            AllergyIntolerance.patient_id == patient_id,
        )
    ).all()
    observations = context.db.scalars(
        select(Observation).where(
            Observation.hospital_id == context.hospital_id,
            Observation.patient_id == patient_id,
        )
    ).all()
    medications = context.db.scalars(
        select(MedicationStatement).where(
            MedicationStatement.hospital_id == context.hospital_id,
            MedicationStatement.patient_id == patient_id,
        )
    ).all()

    items = [
        PatientTimelineItemResponse(
            item_type="appointment",
            id=appointment.id,
            status=appointment.status,
            at=appointment.scheduled_at.date(),
        )
        for appointment in appointments
    ]
    items.extend(
        PatientTimelineItemResponse(
            item_type="encounter",
            id=encounter.id,
            status=encounter.status,
            at=(
                encounter.started_at.date()
                if encounter.started_at is not None
                else encounter.created_at.date()
            ),
        )
        for encounter in encounters
    )
    items.extend(
        [
            *[
                PatientTimelineItemResponse(
                    item_type="condition",
                    id=row.id,
                    status=row.status,
                    at=row.recorded_at.date(),
                )
                for row in conditions
            ],
            *[
                PatientTimelineItemResponse(
                    item_type="allergy",
                    id=row.id,
                    status=row.status,
                    at=(
                        row.reported_at.date()
                        if row.reported_at is not None
                        else row.recorded_at.date()
                    ),
                )
                for row in allergies
            ],
            *[
                PatientTimelineItemResponse(
                    item_type="observation",
                    id=row.id,
                    status="recorded",
                    at=(
                        row.reported_at.date()
                        if row.reported_at is not None
                        else row.recorded_at.date()
                    ),
                )
                for row in observations
            ],
            *[
                PatientTimelineItemResponse(
                    item_type="medication",
                    id=row.id,
                    status=row.status,
                    at=row.recorded_at.date(),
                )
                for row in medications
            ],
        ]
    )
    return sorted(items, key=lambda item: item.at or date.min, reverse=True)


def to_patient_response(patient: Patient) -> PatientResponse:
    return PatientResponse(
        id=patient.id,
        hospital_id=patient.hospital_id,
        synthetic_mrn=patient.synthetic_mrn,
        given_name=patient.given_name,
        family_name=patient.family_name,
        date_of_birth=patient.date_of_birth,
        sex_at_birth=patient.sex_at_birth,
        identity_status=patient.identity_status,
        merged_into_patient_id=patient.merged_into_patient_id,
    )
