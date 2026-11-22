from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MedicineCatalogueItem(Base):
    __tablename__ = "medicine_catalogue_items"
    __table_args__ = (
        UniqueConstraint(
            "catalogue_name",
            "catalogue_version",
            "generic_name",
            "brand_name",
            "strength",
            "dosage_form",
            "route",
            name="uq_medicine_catalogue_items_business_key",
        ),
        CheckConstraint(
            "status IN ('active', 'disabled')",
            name="ck_medicine_catalogue_items_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    catalogue_name: Mapped[str] = mapped_column(String(128), nullable=False)
    catalogue_version: Mapped[str] = mapped_column(String(64), nullable=False)
    generic_name: Mapped[str] = mapped_column(String(255), nullable=False)
    brand_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active_ingredient: Mapped[str | None] = mapped_column(String(255), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    strength: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dosage_form: Mapped[str | None] = mapped_column(String(64), nullable=True)
    route: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prescribing_information: Mapped[str | None] = mapped_column(String, nullable=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_uri: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="active",
        server_default="active",
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

    medication_statements: Mapped[list["MedicationStatement"]] = relationship(
        "MedicationStatement",
        back_populates="catalogue_item",
    )
