from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
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
from app.models.patient import Patient


class PatientIdentifier(Base):
    __tablename__ = "patient_identifiers"
    __table_args__ = (
        UniqueConstraint(
            "hospital_id",
            "id",
            name="uq_patient_identifiers_hospital_id_id",
        ),
        UniqueConstraint(
            "hospital_id",
            "identifier_type",
            "identifier_value",
            name="uq_patient_identifiers_hospital_type_value",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "patient_id"],
            ["patients.hospital_id", "patients.id"],
            name="fk_patient_identifiers_patient_same_hospital",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        Index(
            "ix_patient_identifiers_hospital_patient",
            "hospital_id",
            "patient_id",
        ),
        CheckConstraint(
            "verification_status IN ('verified', 'unverified', 'historical')",
            name="ck_patient_identifiers_verification_status",
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
    identifier_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    identifier_value: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    verification_status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="unverified",
        server_default="unverified",
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
    )

    hospital: Mapped["Hospital"] = relationship(
        back_populates="patient_identifiers",
        overlaps="identifiers,patient",
    )
    patient: Mapped["Patient"] = relationship(
        back_populates="identifiers",
        overlaps="hospital,patient_identifiers",
    )
