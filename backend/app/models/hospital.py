from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Index, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Hospital(Base):
    __tablename__ = "hospitals"
    __table_args__ = (
        UniqueConstraint("id", name="uq_hospitals_id"),
        UniqueConstraint("code", name="uq_hospitals_code"),
        Index("ix_hospitals_status", "status"),
        CheckConstraint(
            "status IN ('active', 'suspended', 'inactive')",
            name="ck_hospitals_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="active",
        server_default="active",
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    hospital_users: Mapped[list["HospitalUser"]] = relationship(
        back_populates="hospital",
    )
    patients: Mapped[list["Patient"]] = relationship(
        back_populates="hospital",
    )
    patient_identifiers: Mapped[list["PatientIdentifier"]] = relationship(
        back_populates="hospital",
    )
    patient_match_candidates: Mapped[
        list["PatientMatchCandidate"]
    ] = relationship(
        back_populates="hospital",
    )
    appointments: Mapped[list["Appointment"]] = relationship(
        back_populates="hospital",
    )
    encounters: Mapped[list["Encounter"]] = relationship(
        back_populates="hospital",
    )
    provenance_records: Mapped[list["ProvenanceRecord"]] = relationship(
        back_populates="hospital",
    )
    conditions: Mapped[list["Condition"]] = relationship(
        back_populates="hospital",
    )
    allergy_intolerances: Mapped[list["AllergyIntolerance"]] = relationship(
        back_populates="hospital",
    )
    observations: Mapped[list["Observation"]] = relationship(
        back_populates="hospital",
    )
    medication_statements: Mapped[list["MedicationStatement"]] = relationship(
        back_populates="hospital",
    )
