from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, Numeric, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DocumentRegion(Base):
    __tablename__ = "document_regions"
    __table_args__ = (
        UniqueConstraint(
            "hospital_id",
            "id",
            name="uq_document_regions_hospital_id_id",
        ),
        UniqueConstraint(
            "hospital_id",
            "id",
            "document_page_id",
            name="uq_document_regions_hospital_id_page",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "document_page_id"],
            ["document_pages.hospital_id", "document_pages.id"],
            name="fk_document_regions_page_same_hospital",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "x IS NULL OR x >= 0",
            name="ck_document_regions_x",
        ),
        CheckConstraint(
            "y IS NULL OR y >= 0",
            name="ck_document_regions_y",
        ),
        CheckConstraint(
            "width IS NULL OR width >= 0",
            name="ck_document_regions_width",
        ),
        CheckConstraint(
            "height IS NULL OR height >= 0",
            name="ck_document_regions_height",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_document_regions_confidence",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    hospital_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hospitals.id", ondelete="RESTRICT"),
        nullable=False,
    )
    document_page_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    region_type: Mapped[str] = mapped_column(String(64), nullable=False)
    x: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    y: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    width: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    height: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    text: Mapped[str | None] = mapped_column(nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)

    page: Mapped["DocumentPage"] = relationship(back_populates="regions")
