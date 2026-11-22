from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ClinicalNoteDraft(Base):
    __tablename__ = "clinical_note_drafts"
    __table_args__ = (
        UniqueConstraint(
            "hospital_id",
            "id",
            name="uq_clinical_note_drafts_hospital_id_id",
        ),
        UniqueConstraint(
            "hospital_id",
            "id",
            "patient_id",
            name="uq_clinical_note_drafts_hospital_id_id_patient_id",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "patient_id"],
            ["patients.hospital_id", "patients.id"],
            name="fk_clinical_note_drafts_patient_same_hospital",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "encounter_id", "patient_id"],
            ["encounters.hospital_id", "encounters.id", "encounters.patient_id"],
            name="fk_clinical_note_drafts_encounter_patient_same",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "created_by_hospital_user_id"],
            ["hospital_users.hospital_id", "hospital_users.id"],
            name="fk_clinical_note_drafts_creator_same_hospital",
            ondelete="RESTRICT",
        ),
        Index(
            "ix_clinical_note_drafts_hospital_patient_created",
            "hospital_id",
            "patient_id",
            "created_at",
        ),
        CheckConstraint(
            "status IN ('draft', 'approved', 'cancelled')",
            name="ck_clinical_note_drafts_status",
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
    transcript_text: Mapped[str] = mapped_column(Text, nullable=False)
    chief_complaint: Mapped[str] = mapped_column(String(255), nullable=False)
    history: Mapped[str] = mapped_column(Text, nullable=False)
    patient_facts: Mapped[str] = mapped_column(Text, nullable=False)
    doctor_questions: Mapped[str] = mapped_column(Text, nullable=False)
    examination_findings: Mapped[str] = mapped_column(Text, nullable=False)
    assessment: Mapped[str] = mapped_column(Text, nullable=False)
    plan: Mapped[str] = mapped_column(Text, nullable=False)
    missing_information: Mapped[str] = mapped_column(Text, nullable=False)
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
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
