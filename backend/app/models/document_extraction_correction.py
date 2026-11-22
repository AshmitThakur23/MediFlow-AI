from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DocumentExtractionCorrection(Base):
    __tablename__ = "document_extraction_corrections"
    __table_args__ = (
        UniqueConstraint(
            "hospital_id",
            "extraction_id",
            "id",
            name="uq_document_extraction_corrections_hospital_extraction_id",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "extraction_id"],
            ["document_extractions.hospital_id", "document_extractions.id"],
            name="fk_document_extraction_corrections_extraction_same_hospital",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "corrected_by_hospital_user_id"],
            ["hospital_users.hospital_id", "hospital_users.id"],
            name="fk_document_extraction_corrections_corrector_same_hospital",
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    hospital_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hospitals.id", ondelete="RESTRICT"),
        nullable=False,
    )
    extraction_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    corrected_by_hospital_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )
    previous_value: Mapped[str | None] = mapped_column(nullable=True)
    corrected_value: Mapped[str] = mapped_column(nullable=False)
    reason: Mapped[str] = mapped_column(nullable=False)
    corrected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    extraction: Mapped["DocumentExtraction"] = relationship(
        back_populates="corrections",
    )
