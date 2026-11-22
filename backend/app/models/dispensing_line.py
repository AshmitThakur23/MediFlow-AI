from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DispensingLine(Base):
    __tablename__ = "dispensing_lines"
    __table_args__ = (
        UniqueConstraint(
            "hospital_id",
            "dispensing_record_id",
            "id",
            name="uq_dispensing_lines_hospital_record_id",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "dispensing_record_id"],
            ["dispensing_records.hospital_id", "dispensing_records.id"],
            name="fk_dispensing_lines_record_same_hospital",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "prescription_line_id"],
            ["prescription_lines.hospital_id", "prescription_lines.id"],
            name="fk_dispensing_lines_prescription_line_same_hospital",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "quantity_prescribed >= 0",
            name="ck_dispensing_lines_quantity_prescribed",
        ),
        CheckConstraint(
            "quantity_dispensed >= 0",
            name="ck_dispensing_lines_quantity_dispensed",
        ),
        CheckConstraint(
            "quantity_dispensed <= quantity_prescribed",
            name="ck_dispensing_lines_quantity_not_exceeded",
        ),
        CheckConstraint(
            "status IN ('pending', 'partial', 'dispensed', 'unavailable')",
            name="ck_dispensing_lines_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    hospital_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hospitals.id", ondelete="RESTRICT"),
        nullable=False,
    )
    dispensing_record_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    prescription_line_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    quantity_prescribed: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    quantity_dispensed: Mapped[Decimal] = mapped_column(
        Numeric(18, 6),
        nullable=False,
        default=Decimal("0"),
    )
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    clarification_text: Mapped[str | None] = mapped_column(nullable=True)
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

    dispensing_record: Mapped["DispensingRecord"] = relationship(back_populates="lines")
