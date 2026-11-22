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


class PrescriptionDraft(Base):
    __tablename__ = "prescription_drafts"
    __table_args__ = (
        UniqueConstraint(
            "hospital_id",
            "id",
            name="uq_prescription_drafts_hospital_id_id",
        ),
        UniqueConstraint(
            "hospital_id",
            "id",
            "patient_id",
            name="uq_prescription_drafts_hospital_id_id_patient_id",
        ),
        UniqueConstraint(
            "hospital_id",
            "id",
            "patient_id",
            "encounter_id",
            name="uq_prescription_drafts_hospital_id_id_patient_encounter",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "patient_id"],
            ["patients.hospital_id", "patients.id"],
            name="fk_prescription_drafts_patient_same_hospital",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "encounter_id", "patient_id"],
            ["encounters.hospital_id", "encounters.id", "encounters.patient_id"],
            name="fk_prescription_drafts_encounter_patient_same",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "created_by_hospital_user_id"],
            ["hospital_users.hospital_id", "hospital_users.id"],
            name="fk_prescription_drafts_creator_same_hospital",
            ondelete="RESTRICT",
        ),
        Index(
            "ix_prescription_drafts_hospital_patient_created",
            "hospital_id",
            "patient_id",
            "created_at",
        ),
        CheckConstraint(
            "status IN ('draft', 'approved', 'cancelled', 'superseded')",
            name="ck_prescription_drafts_status",
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
    created_by_hospital_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )
    ai_output_run_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="draft",
        server_default="draft",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    lines: Mapped[list["PrescriptionDraftLine"]] = relationship(
        back_populates="draft",
    )
