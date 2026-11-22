from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from app.db.base import Base
from app.models.hospital import Hospital
from app.models.hospital_user import HospitalUser
from app.models.patient import Patient


class PatientMatchCandidate(Base):
    __tablename__ = "patient_match_candidates"
    __table_args__ = (
        UniqueConstraint(
            "hospital_id",
            "id",
            name="uq_patient_match_candidates_hospital_id_id",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "candidate_patient_id"],
            ["patients.hospital_id", "patients.id"],
            name="fk_patient_match_candidates_candidate_same_hospital",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "possible_patient_id"],
            ["patients.hospital_id", "patients.id"],
            name="fk_patient_match_candidates_possible_same_hospital",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "reviewed_by_hospital_user_id"],
            ["hospital_users.hospital_id", "hospital_users.id"],
            name="fk_patient_match_candidates_reviewer_same_hospital",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        Index(
            "ix_patient_match_candidates_hospital_status",
            "hospital_id",
            "status",
        ),
        CheckConstraint(
            "candidate_patient_id <> possible_patient_id",
            name="ck_patient_match_candidates_distinct_patients",
        ),
        CheckConstraint(
            "match_score IS NULL OR (match_score >= 0 AND match_score <= 1)",
            name="ck_patient_match_candidates_match_score",
        ),
        CheckConstraint(
            "status IN ('open', 'confirmed_same', 'confirmed_different', 'closed')",
            name="ck_patient_match_candidates_status",
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
    candidate_patient_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )
    possible_patient_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )
    match_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="open",
        server_default="open",
    )
    reviewed_by_hospital_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
    )

    hospital: Mapped["Hospital"] = relationship(
        back_populates="patient_match_candidates",
        overlaps=(
            "reviewed_match_candidates,match_candidates_as_candidate,"
            "match_candidates_as_possible"
        ),
    )
    candidate_patient: Mapped["Patient"] = relationship(
        "Patient",
        foreign_keys=lambda: [PatientMatchCandidate.candidate_patient_id],
        primaryjoin=lambda: (
            (foreign(PatientMatchCandidate.hospital_id) == Patient.hospital_id)
            & (
                foreign(PatientMatchCandidate.candidate_patient_id)
                == Patient.id
            )
        ),
        back_populates="match_candidates_as_candidate",
        overlaps=(
            "hospital,patient_match_candidates,reviewed_match_candidates,"
            "match_candidates_as_possible"
        ),
    )
    possible_patient: Mapped["Patient"] = relationship(
        "Patient",
        foreign_keys=lambda: [PatientMatchCandidate.possible_patient_id],
        primaryjoin=lambda: (
            (foreign(PatientMatchCandidate.hospital_id) == Patient.hospital_id)
            & (
                foreign(PatientMatchCandidate.possible_patient_id)
                == Patient.id
            )
        ),
        back_populates="match_candidates_as_possible",
        overlaps=(
            "hospital,patient_match_candidates,reviewed_match_candidates,"
            "match_candidates_as_candidate,candidate_patient"
        ),
    )
    reviewed_by_hospital_user: Mapped["HospitalUser | None"] = relationship(
        "HospitalUser",
        foreign_keys=lambda: [
            PatientMatchCandidate.reviewed_by_hospital_user_id
        ],
        primaryjoin=lambda: (
            (
                foreign(PatientMatchCandidate.hospital_id)
                == HospitalUser.hospital_id
            )
            & (
                foreign(PatientMatchCandidate.reviewed_by_hospital_user_id)
                == HospitalUser.id
            )
        ),
        back_populates="reviewed_match_candidates",
        overlaps=(
            "hospital,patient_match_candidates,match_candidates_as_candidate,"
            "match_candidates_as_possible,candidate_patient,possible_patient"
        ),
    )
