from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DocumentPage(Base):
    __tablename__ = "document_pages"
    __table_args__ = (
        UniqueConstraint(
            "hospital_id",
            "id",
            name="uq_document_pages_hospital_id_id",
        ),
        UniqueConstraint(
            "hospital_id",
            "document_id",
            "page_number",
            name="uq_document_pages_hospital_document_page",
        ),
        UniqueConstraint(
            "hospital_id",
            "id",
            "document_id",
            name="uq_document_pages_hospital_id_document",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "document_id"],
            ["medical_documents.hospital_id", "medical_documents.id"],
            name="fk_document_pages_document_same_hospital",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "page_number > 0",
            name="ck_document_pages_page_number",
        ),
        CheckConstraint(
            "width IS NULL OR width >= 0",
            name="ck_document_pages_width",
        ),
        CheckConstraint(
            "height IS NULL OR height >= 0",
            name="ck_document_pages_height",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    hospital_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hospitals.id", ondelete="RESTRICT"),
        nullable=False,
    )
    document_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    page_number: Mapped[int] = mapped_column(nullable=False)
    width: Mapped[float | None] = mapped_column(nullable=True)
    height: Mapped[float | None] = mapped_column(nullable=True)
    text_source: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    document: Mapped["MedicalDocument"] = relationship(back_populates="pages")
    regions: Mapped[list["DocumentRegion"]] = relationship(back_populates="page")
