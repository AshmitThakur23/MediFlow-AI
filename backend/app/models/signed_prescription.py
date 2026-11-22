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


class SignedPrescription(Base):
    __tablename__ = "signed_prescriptions"
    __table_args__ = (
        UniqueConstraint(
            "hospital_id",
            "id",
            name="uq_signed_prescriptions_hospital_id_id",
        ),
        UniqueConstraint(
            "hospital_id",
            "id",
            "patient_id",
            name="uq_signed_prescriptions_hospital_id_id_patient_id",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "patient_id"],
            ["patients.hospital_id", "patients.id"],
            name="fk_signed_prescriptions_patient_same_hospital",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "encounter_id", "patient_id"],
            ["encounters.hospital_id", "encounters.id", "encounters.patient_id"],
            name="fk_signed_prescriptions_encounter_patient_same",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "draft_id", "patient_id", "encounter_id"],
            [
                "prescription_drafts.hospital_id",
                "prescription_drafts.id",
                "prescription_drafts.patient_id",
                "prescription_drafts.encounter_id",
            ],
            name="fk_signed_prescriptions_draft_patient_encounter",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "prescribing_hospital_user_id"],
            ["hospital_users.hospital_id", "hospital_users.id"],
            name="fk_signed_prescriptions_prescriber_same_hospital",
            ondelete="RESTRICT",
        ),
        Index(
            "ix_signed_prescriptions_hospital_patient_signed",
            "hospital_id",
            "patient_id",
            "signed_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    hospital_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hospitals.id", ondelete="RESTRICT"),
        nullable=False,
    )
    patient_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    encounter_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    draft_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    prescribing_hospital_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )
    signed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    signature_reference: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    lines: Mapped[list["PrescriptionLine"]] = relationship(back_populates="prescription")
