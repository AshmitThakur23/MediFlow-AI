from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import (
    AuthorizationContext,
    require_patient_object_access,
    require_roles,
)
from app.models.appointment import Appointment
from app.models.encounter import Encounter
from app.models.hospital_user import HospitalUser
from app.models.patient import Patient


router = APIRouter(prefix="/encounters", tags=["encounters"])
ENCOUNTER_STATUSES = {"planned", "in_progress", "completed", "cancelled"}


def ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class EncounterCreateRequest(BaseModel):
    patient_id: UUID
    appointment_id: UUID | None = None
    doctor_hospital_user_id: UUID
    started_at: datetime | None = None
    ended_at: datetime | None = None
    status: str = "planned"


class EncounterStatusRequest(BaseModel):
    status: str
    started_at: datetime | None = None
    ended_at: datetime | None = None


class EncounterResponse(BaseModel):
    id: UUID
    hospital_id: UUID
    patient_id: UUID
    appointment_id: UUID | None
    doctor_hospital_user_id: UUID
    started_at: datetime | None
    ended_at: datetime | None
    status: str


@router.post(
    "",
    response_model=EncounterResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_encounter(
    request: EncounterCreateRequest,
    context: AuthorizationContext = Depends(require_roles("doctor", "staff")),
) -> EncounterResponse:
    require_patient_object_access(context, request.patient_id)
    if request.status not in ENCOUNTER_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid encounter status",
        )
    if (
        request.started_at is not None
        and request.ended_at is not None
        and request.ended_at < request.started_at
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Encounter end time cannot precede start time",
        )

    patient = context.db.scalar(
        select(Patient).where(
            Patient.hospital_id == context.hospital_id,
            Patient.id == request.patient_id,
        )
    )
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found in the requested hospital",
        )
    doctor = context.db.scalar(
        select(HospitalUser).where(
            HospitalUser.hospital_id == context.hospital_id,
            HospitalUser.id == request.doctor_hospital_user_id,
            HospitalUser.status == "active",
        )
    )
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor assignment not found in the requested hospital",
        )
    if request.appointment_id is not None:
        appointment = context.db.scalar(
            select(Appointment).where(
                Appointment.hospital_id == context.hospital_id,
                Appointment.id == request.appointment_id,
            )
        )
        if appointment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found in the requested hospital",
            )
        if appointment.patient_id != request.patient_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Encounter patient does not match appointment patient",
            )

    encounter = Encounter(
        hospital_id=context.hospital_id,
        patient_id=request.patient_id,
        appointment_id=request.appointment_id,
        doctor_hospital_user_id=request.doctor_hospital_user_id,
        started_at=request.started_at,
        ended_at=request.ended_at,
        status=request.status,
    )
    context.db.add(encounter)
    try:
        context.db.commit()
    except IntegrityError as exc:
        context.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Encounter violates tenant, patient, or time constraints",
        ) from exc
    context.db.refresh(encounter)
    return to_encounter_response(encounter)


@router.get("", response_model=list[EncounterResponse])
def list_encounters(
    context: AuthorizationContext = Depends(require_roles("doctor", "staff")),
) -> list[EncounterResponse]:
    encounters = context.db.scalars(
        select(Encounter).where(
            Encounter.hospital_id == context.hospital_id,
        )
    ).all()
    return [to_encounter_response(encounter) for encounter in encounters]


@router.get("/{encounter_id}", response_model=EncounterResponse)
def get_encounter(
    encounter_id: UUID,
    context: AuthorizationContext = Depends(require_roles("doctor", "staff")),
) -> EncounterResponse:
    encounter = context.db.scalar(
        select(Encounter).where(
            Encounter.hospital_id == context.hospital_id,
            Encounter.id == encounter_id,
        )
    )
    if encounter is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Encounter not found",
        )
    return to_encounter_response(encounter)


@router.patch("/{encounter_id}/status", response_model=EncounterResponse)
def update_encounter_status(
    encounter_id: UUID,
    request: EncounterStatusRequest,
    context: AuthorizationContext = Depends(require_roles("doctor")),
) -> EncounterResponse:
    if request.status not in ENCOUNTER_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid encounter status",
        )
    encounter = context.db.scalar(
        select(Encounter).where(
            Encounter.hospital_id == context.hospital_id,
            Encounter.id == encounter_id,
        )
    )
    if encounter is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Encounter not found",
        )

    started_at = ensure_timezone_aware(
        request.started_at
        if request.started_at is not None
        else encounter.started_at
    )
    ended_at = ensure_timezone_aware(
        request.ended_at
        if request.ended_at is not None
        else encounter.ended_at
    )
    if (
        started_at is not None
        and ended_at is not None
        and ended_at < started_at
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Encounter end time cannot precede start time",
        )
    encounter.status = request.status
    encounter.started_at = started_at
    encounter.ended_at = ended_at
    try:
        context.db.commit()
    except IntegrityError as exc:
        context.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Encounter status update was rejected",
        ) from exc
    context.db.refresh(encounter)
    return to_encounter_response(encounter)


def to_encounter_response(encounter: Encounter) -> EncounterResponse:
    return EncounterResponse(
        id=encounter.id,
        hospital_id=encounter.hospital_id,
        patient_id=encounter.patient_id,
        appointment_id=encounter.appointment_id,
        doctor_hospital_user_id=encounter.doctor_hospital_user_id,
        started_at=encounter.started_at,
        ended_at=encounter.ended_at,
        status=encounter.status,
    )
