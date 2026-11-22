from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'disabled')",
            name="ck_users_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    email: Mapped[str | None] = mapped_column(
        String(320),
        unique=True,
        nullable=True,
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="active",
        server_default="active",
    )
    identity_subject: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
    )
    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    hospital_users: Mapped[list["HospitalUser"]] = relationship(
        back_populates="user",
    )
