from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.hospital import Hospital
from app.models.hospital_user import HospitalUser
from app.models.patient import Patient


def _encounter_column(name: str):
    from app.models.encounter import Encounter

    return getattr(Encounter, name)


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        UniqueConstraint(
            "hospital_id",
            "id",
            name="uq_appointments_hospital_id_id",
        ),
        UniqueConstraint(
            "hospital_id",
            "id",
            "patient_id",
            name="uq_appointments_hospital_id_id_patient_id",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "patient_id"],
            ["patients.hospital_id", "patients.id"],
            name="fk_appointments_patient_same_hospital",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "doctor_hospital_user_id"],
            ["hospital_users.hospital_id", "hospital_users.id"],
            name="fk_appointments_doctor_same_hospital",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        Index(
            "ix_appointments_hospital_doctor_scheduled",
            "hospital_id",
            "doctor_hospital_user_id",
            "scheduled_at",
        ),
        Index(
            "ix_appointments_hospital_patient_scheduled",
            "hospital_id",
            "patient_id",
            "scheduled_at",
        ),
        CheckConstraint(
            "status IN ('scheduled', 'checked_in', 'cancelled', "
            "'completed', 'no_show')",
            name="ck_appointments_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    hospital_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hospitals.id", ondelete="RESTRICT"),
        nullable=False,
    )
    patient_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )
    doctor_hospital_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="scheduled",
        server_default="scheduled",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    hospital: Mapped["Hospital"] = relationship(
        back_populates="appointments",
        overlaps="appointments",
    )
    patient: Mapped["Patient"] = relationship(
        back_populates="appointments",
        overlaps="hospital,appointments",
    )
    doctor_hospital_user: Mapped["HospitalUser"] = relationship(
        back_populates="appointments",
        overlaps="hospital,patient,appointments",
    )
    encounter: Mapped["Encounter | None"] = relationship(
        "Encounter",
        back_populates="appointment",
        foreign_keys=lambda: [
            _encounter_column("hospital_id"),
            _encounter_column("appointment_id"),
            _encounter_column("patient_id"),
        ],
        primaryjoin=lambda: (
            (_encounter_column("hospital_id") == Appointment.hospital_id)
            & (_encounter_column("appointment_id") == Appointment.id)
            & (_encounter_column("patient_id") == Appointment.patient_id)
        ),
        uselist=False,
        overlaps=(
            "hospital,patient,doctor_hospital_user,appointments,encounters"
        ),
    )
