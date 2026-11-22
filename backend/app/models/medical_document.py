from datetime import date, datetime
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


class MedicalDocument(Base):
    __tablename__ = "medical_documents"
    __table_args__ = (
        UniqueConstraint("hospital_id", "id", name="uq_medical_documents_hospital_id_id"),
        UniqueConstraint(
            "hospital_id",
            "id",
            "patient_id",
            name="uq_medical_documents_hospital_id_id_patient_id",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "patient_id"],
            ["patients.hospital_id", "patients.id"],
            name="fk_medical_documents_patient_same_hospital",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "encounter_id", "patient_id"],
            ["encounters.hospital_id", "encounters.id", "encounters.patient_id"],
            name="fk_medical_documents_encounter_patient_same",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "uploaded_by_hospital_user_id"],
            ["hospital_users.hospital_id", "hospital_users.id"],
            name="fk_medical_documents_uploader_same_hospital",
            ondelete="RESTRICT",
        ),
        Index(
            "ix_medical_documents_hospital_patient_date",
            "hospital_id",
            "patient_id",
            "document_date",
        ),
        CheckConstraint(
            "page_count IS NULL OR page_count > 0",
            name="ck_medical_documents_page_count",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    hospital_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hospitals.id", ondelete="RESTRICT"),
        nullable=False,
    )
    patient_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    encounter_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    document_type: Mapped[str] = mapped_column(String(64), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    object_uri: Mapped[str] = mapped_column(String(2048), nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    document_date: Mapped[date | None] = mapped_column(nullable=True)
    upload_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    issuing_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    page_count: Mapped[int | None] = mapped_column(nullable=True)
    processing_status: Mapped[str] = mapped_column(String(24), nullable=False)
    retention_status: Mapped[str] = mapped_column(String(24), nullable=False)
    uploaded_by_hospital_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )

    pages: Mapped[list["DocumentPage"]] = relationship(
        back_populates="document",
    )
