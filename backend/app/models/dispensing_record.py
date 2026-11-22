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


class DispensingRecord(Base):
    __tablename__ = "dispensing_records"
    __table_args__ = (
        UniqueConstraint(
            "hospital_id",
            "id",
            name="uq_dispensing_records_hospital_id_id",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "patient_id"],
            ["patients.hospital_id", "patients.id"],
            name="fk_dispensing_records_patient_same_hospital",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "prescription_id", "patient_id"],
            [
                "signed_prescriptions.hospital_id",
                "signed_prescriptions.id",
                "signed_prescriptions.patient_id",
            ],
            name="fk_dispensing_records_prescription_patient_same",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "pharmacist_hospital_user_id"],
            ["hospital_users.hospital_id", "hospital_users.id"],
            name="fk_dispensing_records_pharmacist_same_hospital",
            ondelete="RESTRICT",
        ),
        Index(
            "ix_dispensing_records_hospital_status_created",
            "hospital_id",
            "status",
            "created_at",
        ),
        CheckConstraint(
            "status IN ('viewed', 'dispensing', 'partially_dispensed', "
            "'dispensed', 'clarification_requested', 'cancelled')",
            name="ck_dispensing_records_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    hospital_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hospitals.id", ondelete="RESTRICT"),
        nullable=False,
    )
    patient_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    prescription_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    pharmacist_hospital_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    substitution_allowed: Mapped[bool] = mapped_column(nullable=False, default=False)
    substitution_text: Mapped[str | None] = mapped_column(nullable=True)
    clarification_text: Mapped[str | None] = mapped_column(nullable=True)
    dispensed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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

    lines: Mapped[list["DispensingLine"]] = relationship(back_populates="dispensing_record")
