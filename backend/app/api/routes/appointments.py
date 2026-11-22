from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import (
    AuthorizationContext,
    require_patient_object_access,
    require_roles,
)
from app.models.appointment import Appointment
from app.models.hospital_user import HospitalUser
from app.models.patient import Patient


router = APIRouter(prefix="/appointments", tags=["appointments"])
APPOINTMENT_STATUSES = {
    "scheduled",
    "checked_in",
    "cancelled",
    "completed",
    "no_show",
}


class AppointmentCreateRequest(BaseModel):
    patient_id: UUID
    doctor_hospital_user_id: UUID
    scheduled_at: datetime


class AppointmentStatusRequest(BaseModel):
    status: str


class AppointmentResponse(BaseModel):
    id: UUID
    hospital_id: UUID
    patient_id: UUID
    doctor_hospital_user_id: UUID
    scheduled_at: datetime
    status: str


@router.post(
    "",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_appointment(
    request: AppointmentCreateRequest,
    context: AuthorizationContext = Depends(require_roles("doctor", "staff")),
) -> AppointmentResponse:
    require_patient_object_access(context, request.patient_id)
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

    appointment = Appointment(
        hospital_id=context.hospital_id,
        patient_id=request.patient_id,
        doctor_hospital_user_id=request.doctor_hospital_user_id,
        scheduled_at=request.scheduled_at,
        status="scheduled",
    )
    context.db.add(appointment)
    try:
        context.db.commit()
    except IntegrityError as exc:
        context.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Appointment violates tenant or patient constraints",
        ) from exc
    context.db.refresh(appointment)
    return to_appointment_response(appointment)


@router.get("", response_model=list[AppointmentResponse])
def list_appointments(
    patient_id: UUID | None = Query(default=None),
    context: AuthorizationContext = Depends(
        require_roles("doctor", "staff")
    ),
) -> list[AppointmentResponse]:
    statement = select(Appointment).where(
        Appointment.hospital_id == context.hospital_id,
    )
    if patient_id is not None:
        statement = statement.where(Appointment.patient_id == patient_id)
    appointments = context.db.scalars(statement).all()
    return [
        to_appointment_response(appointment)
        for appointment in appointments
    ]


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: UUID,
    context: AuthorizationContext = Depends(
        require_roles("doctor", "staff")
    ),
) -> AppointmentResponse:
    appointment = context.db.scalar(
        select(Appointment).where(
            Appointment.hospital_id == context.hospital_id,
            Appointment.id == appointment_id,
        )
    )
    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
    return to_appointment_response(appointment)


@router.patch("/{appointment_id}/status", response_model=AppointmentResponse)
def update_appointment_status(
    appointment_id: UUID,
    request: AppointmentStatusRequest,
    context: AuthorizationContext = Depends(require_roles("doctor", "staff")),
) -> AppointmentResponse:
    if request.status not in APPOINTMENT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid appointment status",
        )
    appointment = context.db.scalar(
        select(Appointment).where(
            Appointment.hospital_id == context.hospital_id,
            Appointment.id == appointment_id,
        )
    )
    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
    appointment.status = request.status
    try:
        context.db.commit()
    except IntegrityError as exc:
        context.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Appointment status update was rejected",
        ) from exc
    context.db.refresh(appointment)
    return to_appointment_response(appointment)


def to_appointment_response(appointment: Appointment) -> AppointmentResponse:
    return AppointmentResponse(
        id=appointment.id,
        hospital_id=appointment.hospital_id,
        patient_id=appointment.patient_id,
        doctor_hospital_user_id=appointment.doctor_hospital_user_id,
        scheduled_at=appointment.scheduled_at,
        status=appointment.status,
    )
