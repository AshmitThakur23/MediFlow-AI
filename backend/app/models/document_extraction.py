from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Numeric,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DocumentExtraction(Base):
    __tablename__ = "document_extractions"
    __table_args__ = (
        UniqueConstraint(
            "hospital_id",
            "id",
            name="uq_document_extractions_hospital_id_id",
        ),
        UniqueConstraint(
            "hospital_id",
            "id",
            "document_id",
            name="uq_document_extractions_hospital_id_document",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "document_id"],
            ["medical_documents.hospital_id", "medical_documents.id"],
            name="fk_document_extractions_document_same_hospital",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "document_region_id"],
            ["document_regions.hospital_id", "document_regions.id"],
            name="fk_document_extractions_region_same_hospital",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "reviewed_by_hospital_user_id"],
            ["hospital_users.hospital_id", "hospital_users.id"],
            name="fk_document_extractions_reviewer_same_hospital",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_document_extractions_confidence",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    hospital_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hospitals.id", ondelete="RESTRICT"),
        nullable=False,
    )
    document_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    document_region_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    field_name: Mapped[str] = mapped_column(nullable=False)
    extracted_value: Mapped[str | None] = mapped_column(nullable=True)
    normalized_value: Mapped[str | None] = mapped_column(nullable=True)
    unit: Mapped[str | None] = mapped_column(nullable=True)
    reference_range: Mapped[str | None] = mapped_column(nullable=True)
    extraction_status: Mapped[str] = mapped_column(nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    reviewed_by_hospital_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    corrections: Mapped[list["DocumentExtractionCorrection"]] = relationship(
        back_populates="extraction",
    )
