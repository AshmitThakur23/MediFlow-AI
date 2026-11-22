from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, ForeignKeyConstraint, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PrescriptionDraftLine(Base):
    __tablename__ = "prescription_draft_lines"
    __table_args__ = (
        UniqueConstraint(
            "hospital_id",
            "draft_id",
            "id",
            name="uq_prescription_draft_lines_hospital_draft_id",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "draft_id"],
            ["prescription_drafts.hospital_id", "prescription_drafts.id"],
            name="fk_prescription_draft_lines_draft_same_hospital",
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    hospital_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hospitals.id", ondelete="RESTRICT"),
        nullable=False,
    )
    draft_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    catalogue_item_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("medicine_catalogue_items.id", ondelete="RESTRICT"),
        nullable=True,
    )
    medicine_name: Mapped[str] = mapped_column(nullable=False)
    strength: Mapped[str | None] = mapped_column(nullable=True)
    dose: Mapped[str | None] = mapped_column(nullable=True)
    route: Mapped[str | None] = mapped_column(nullable=True)
    frequency: Mapped[str | None] = mapped_column(nullable=True)
    duration: Mapped[str | None] = mapped_column(nullable=True)
    quantity: Mapped[str | None] = mapped_column(nullable=True)
    instructions: Mapped[str | None] = mapped_column(nullable=True)

    draft: Mapped["PrescriptionDraft"] = relationship(back_populates="lines")
