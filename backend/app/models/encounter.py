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
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from app.db.base import Base
from app.models.appointment import Appointment
from app.models.hospital import Hospital
from app.models.hospital_user import HospitalUser
from app.models.patient import Patient


def _provenance_column(name: str):
    from app.models.provenance_record import ProvenanceRecord

    return getattr(ProvenanceRecord, name)


def _typed_fact_column(model_name: str, name: str):
    module_name = {
        "Condition": "condition",
        "AllergyIntolerance": "allergy_intolerance",
        "Observation": "observation",
        "MedicationStatement": "medication_statement",
    }[model_name]
    module = __import__(
        f"app.models.{module_name}",
        fromlist=[model_name],
    )
    return getattr(module, model_name).__dict__[name]


class Encounter(Base):
    __tablename__ = "encounters"
    __table_args__ = (
        UniqueConstraint(
            "hospital_id",
            "id",
            name="uq_encounters_hospital_id_id",
        ),
        UniqueConstraint(
            "hospital_id",
            "id",
            "patient_id",
            name="uq_encounters_hospital_id_id_patient_id",
        ),
        UniqueConstraint(
            "hospital_id",
            "appointment_id",
            name="uq_encounters_hospital_appointment",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "patient_id"],
            ["patients.hospital_id", "patients.id"],
            name="fk_encounters_patient_same_hospital",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "appointment_id"],
            ["appointments.hospital_id", "appointments.id"],
            name="fk_encounters_appointment_same_hospital",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "appointment_id", "patient_id"],
            [
                "appointments.hospital_id",
                "appointments.id",
                "appointments.patient_id",
            ],
            name="fk_encounters_appointment_patient_same",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "doctor_hospital_user_id"],
            ["hospital_users.hospital_id", "hospital_users.id"],
            name="fk_encounters_doctor_same_hospital",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        Index(
            "ix_encounters_hospital_patient_started",
            "hospital_id",
            "patient_id",
            "started_at",
        ),
        Index(
            "ix_encounters_hospital_doctor_started",
            "hospital_id",
            "doctor_hospital_user_id",
            "started_at",
        ),
        CheckConstraint(
            "status IN ('planned', 'in_progress', 'completed', 'cancelled')",
            name="ck_encounters_status",
        ),
        CheckConstraint(
            "ended_at IS NULL OR started_at IS NULL OR ended_at >= started_at",
            name="ck_encounters_time_order",
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
    appointment_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )
    doctor_hospital_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="planned",
        server_default="planned",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    hospital: Mapped["Hospital"] = relationship(
        back_populates="encounters",
        overlaps="encounters",
    )
    patient: Mapped["Patient"] = relationship(
        back_populates="encounters",
        overlaps="hospital,encounters",
    )
    appointment: Mapped["Appointment | None"] = relationship(
        "Appointment",
        back_populates="encounter",
        foreign_keys=lambda: [
            Encounter.hospital_id,
            Encounter.appointment_id,
            Encounter.patient_id,
        ],
        primaryjoin=lambda: (
            (Encounter.hospital_id == Appointment.hospital_id)
            & (Encounter.appointment_id == Appointment.id)
            & (Encounter.patient_id == Appointment.patient_id)
        ),
        overlaps=(
            "hospital,patient,doctor_hospital_user,encounters,appointments"
        ),
    )
    doctor_hospital_user: Mapped["HospitalUser"] = relationship(
        back_populates="encounters",
        overlaps="hospital,patient,encounters",
    )
    provenance_records: Mapped[list["ProvenanceRecord"]] = relationship(
        back_populates="encounter",
        foreign_keys=lambda: [
            _provenance_column("hospital_id"),
            _provenance_column("encounter_id"),
        ],
        primaryjoin=lambda: (
            (
                foreign(_provenance_column("hospital_id"))
                == Encounter.hospital_id
            )
            & (
                foreign(_provenance_column("encounter_id"))
                == Encounter.id
            )
        ),
        overlaps="hospital,provenance_records",
    )
    conditions: Mapped[list["Condition"]] = relationship(
        back_populates="encounter",
        foreign_keys=lambda: [
            _typed_fact_column("Condition", "hospital_id"),
            _typed_fact_column("Condition", "encounter_id"),
        ],
        primaryjoin=lambda: (
            (
                foreign(_typed_fact_column("Condition", "hospital_id"))
                == Encounter.hospital_id
            )
            & (
                foreign(_typed_fact_column("Condition", "encounter_id"))
                == Encounter.id
            )
        ),
        overlaps="hospital,patient,encounter,conditions",
    )
    allergy_intolerances: Mapped[list["AllergyIntolerance"]] = relationship(
        back_populates="encounter",
        foreign_keys=lambda: [
            _typed_fact_column("AllergyIntolerance", "hospital_id"),
            _typed_fact_column("AllergyIntolerance", "encounter_id"),
        ],
        primaryjoin=lambda: (
            (
                foreign(
                    _typed_fact_column("AllergyIntolerance", "hospital_id")
                )
                == Encounter.hospital_id
            )
            & (
                foreign(
                    _typed_fact_column("AllergyIntolerance", "encounter_id")
                )
                == Encounter.id
            )
        ),
        overlaps="hospital,patient,encounter,allergy_intolerances",
    )
    observations: Mapped[list["Observation"]] = relationship(
        back_populates="encounter",
        foreign_keys=lambda: [
            _typed_fact_column("Observation", "hospital_id"),
            _typed_fact_column("Observation", "encounter_id"),
        ],
        primaryjoin=lambda: (
            (
                foreign(_typed_fact_column("Observation", "hospital_id"))
                == Encounter.hospital_id
            )
            & (
                foreign(_typed_fact_column("Observation", "encounter_id"))
                == Encounter.id
            )
        ),
        overlaps="hospital,patient,encounter,observations",
    )
    medication_statements: Mapped[list["MedicationStatement"]] = relationship(
        back_populates="encounter",
        foreign_keys=lambda: [
            _typed_fact_column("MedicationStatement", "hospital_id"),
            _typed_fact_column("MedicationStatement", "encounter_id"),
        ],
        primaryjoin=lambda: (
            (
                foreign(_typed_fact_column("MedicationStatement", "hospital_id"))
                == Encounter.hospital_id
            )
            & (
                foreign(_typed_fact_column("MedicationStatement", "encounter_id"))
                == Encounter.id
            )
        ),
        overlaps="hospital,patient,encounter,medication_statements",
    )
