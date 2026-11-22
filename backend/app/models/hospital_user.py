from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from app.db.base import Base


def _provenance_column(name: str):
    from app.models.provenance_record import ProvenanceRecord

    return getattr(ProvenanceRecord, name)


class HospitalUser(Base):
    __tablename__ = "hospital_users"
    __table_args__ = (
        UniqueConstraint("hospital_id", "id", name="uq_hospital_users_hospital_id_id"),
        UniqueConstraint(
            "hospital_id",
            "user_id",
            "role_code",
            "valid_from",
            name="uq_hospital_users_assignment",
        ),
        Index("ix_hospital_users_hospital_user", "hospital_id", "user_id"),
        Index("ix_hospital_users_status", "hospital_id", "status"),
        CheckConstraint(
            "relationship_scope IN ('hospital', 'department', 'patient_relationship')",
            name="ck_hospital_users_relationship_scope",
        ),
        CheckConstraint(
            "status IN ('active', 'suspended', 'expired')",
            name="ck_hospital_users_status",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_until >= valid_from",
            name="ck_hospital_users_valid_period",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    hospital_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hospitals.id", ondelete="RESTRICT"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    role_code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    relationship_scope: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="hospital",
        server_default="hospital",
    )
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="active",
        server_default="active",
    )
    valid_from: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
    )
    valid_until: Mapped[datetime | None] = mapped_column(
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

    hospital: Mapped["Hospital"] = relationship(
        back_populates="hospital_users",
    )
    user: Mapped["User"] = relationship(
        back_populates="hospital_users",
    )
    reviewed_match_candidates: Mapped[
        list["PatientMatchCandidate"]
    ] = relationship(
        "PatientMatchCandidate",
        back_populates="reviewed_by_hospital_user",
        overlaps=(
            "hospital,patient_match_candidates,match_candidates_as_candidate,"
            "match_candidates_as_possible"
        ),
    )
    appointments: Mapped[list["Appointment"]] = relationship(
        back_populates="doctor_hospital_user",
        overlaps="appointments",
    )
    encounters: Mapped[list["Encounter"]] = relationship(
        back_populates="doctor_hospital_user",
        overlaps="encounters",
    )
    provenance_records: Mapped[list["ProvenanceRecord"]] = relationship(
        back_populates="author_hospital_user",
        foreign_keys=lambda: [
            _provenance_column("hospital_id"),
            _provenance_column("author_hospital_user_id"),
        ],
        primaryjoin=lambda: (
            (
                foreign(_provenance_column("hospital_id"))
                == HospitalUser.hospital_id
            )
            & (
                foreign(_provenance_column("author_hospital_user_id"))
                == HospitalUser.id
            )
        ),
        overlaps="hospital,patient,encounter,provenance_records",
    )
