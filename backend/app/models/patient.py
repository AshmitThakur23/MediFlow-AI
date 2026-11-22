from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship, remote

from app.db.base import Base


def _match_candidate_column(name: str):
    from app.models.patient_match_candidate import PatientMatchCandidate

    return getattr(PatientMatchCandidate, name)


def _provenance_column(name: str):
    from app.models.provenance_record import ProvenanceRecord

    return getattr(ProvenanceRecord, name)


def _typed_fact_column(model_name: str, name: str):
    module_name = {
        "Condition": "condition",
        "AllergyIntolerance": "allergy_intolerance",
        "Observation": "observation",
        "MedicationStatement": "medication_statement",
    }[model_name]
    module = __import__(
        f"app.models.{module_name}",
        fromlist=[model_name],
    )
    return getattr(module, model_name).__dict__[name]


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = (
        UniqueConstraint("hospital_id", "id", name="uq_patients_hospital_id_id"),
        UniqueConstraint(
            "hospital_id",
            "synthetic_mrn",
            name="uq_patients_hospital_synthetic_mrn",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "merged_into_patient_id"],
            ["patients.hospital_id", "patients.id"],
            name="fk_patients_merged_same_hospital",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        Index(
            "ix_patients_hospital_status",
            "hospital_id",
            "identity_status",
        ),
        CheckConstraint(
            "identity_status IN ('verified', 'probable', 'unverified', 'merged')",
            name="ck_patients_identity_status",
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
    synthetic_mrn: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    given_name: Mapped[str] = mapped_column(String(128), nullable=False)
    family_name: Mapped[str] = mapped_column(String(128), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(nullable=False)
    sex_at_birth: Mapped[str | None] = mapped_column(
        String(24),
        nullable=True,
    )
    identity_status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="unverified",
        server_default="unverified",
    )
    merged_into_patient_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
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
        back_populates="patients",
    )
    identifiers: Mapped[list["PatientIdentifier"]] = relationship(
        back_populates="patient",
        overlaps="hospital,patient_identifiers",
    )
    match_candidates_as_candidate: Mapped[
        list["PatientMatchCandidate"]
    ] = relationship(
        "PatientMatchCandidate",
        foreign_keys=lambda: [
            _match_candidate_column("candidate_patient_id")
        ],
        primaryjoin=lambda: (
            (
                foreign(_match_candidate_column("hospital_id"))
                == Patient.hospital_id
            )
            & (
                foreign(_match_candidate_column("candidate_patient_id"))
                == Patient.id
            )
        ),
        back_populates="candidate_patient",
        overlaps=(
            "hospital,patient_match_candidates,reviewed_match_candidates,"
            "match_candidates_as_possible"
        ),
    )
    match_candidates_as_possible: Mapped[
        list["PatientMatchCandidate"]
    ] = relationship(
        "PatientMatchCandidate",
        foreign_keys=lambda: [
            _match_candidate_column("possible_patient_id")
        ],
        primaryjoin=lambda: (
            (
                foreign(_match_candidate_column("hospital_id"))
                == Patient.hospital_id
            )
            & (
                foreign(_match_candidate_column("possible_patient_id"))
                == Patient.id
            )
        ),
        back_populates="possible_patient",
        overlaps=(
            "hospital,patient_match_candidates,reviewed_match_candidates,"
            "match_candidates_as_candidate"
        ),
    )
    appointments: Mapped[list["Appointment"]] = relationship(
        back_populates="patient",
        overlaps="appointments",
    )
    encounters: Mapped[list["Encounter"]] = relationship(
        back_populates="patient",
        overlaps="encounters",
    )
    provenance_records: Mapped[list["ProvenanceRecord"]] = relationship(
        back_populates="patient",
        foreign_keys=lambda: [
            _provenance_column("hospital_id"),
            _provenance_column("patient_id"),
        ],
        primaryjoin=lambda: (
            (
                foreign(_provenance_column("hospital_id"))
                == Patient.hospital_id
            )
            & (foreign(_provenance_column("patient_id")) == Patient.id)
        ),
        overlaps="hospital,provenance_records",
    )
    conditions: Mapped[list["Condition"]] = relationship(
        back_populates="patient",
        foreign_keys=lambda: [
            _typed_fact_column("Condition", "hospital_id"),
            _typed_fact_column("Condition", "patient_id"),
        ],
        primaryjoin=lambda: (
            (
                foreign(_typed_fact_column("Condition", "hospital_id"))
                == Patient.hospital_id
            )
            & (
                foreign(_typed_fact_column("Condition", "patient_id"))
                == Patient.id
            )
        ),
        overlaps="hospital,patient,conditions",
    )
    allergy_intolerances: Mapped[list["AllergyIntolerance"]] = relationship(
        back_populates="patient",
        foreign_keys=lambda: [
            _typed_fact_column("AllergyIntolerance", "hospital_id"),
            _typed_fact_column("AllergyIntolerance", "patient_id"),
        ],
        primaryjoin=lambda: (
            (
                foreign(_typed_fact_column("AllergyIntolerance", "hospital_id"))
                == Patient.hospital_id
            )
            & (
                foreign(_typed_fact_column("AllergyIntolerance", "patient_id"))
                == Patient.id
            )
        ),
        overlaps="hospital,patient,allergy_intolerances",
    )
    observations: Mapped[list["Observation"]] = relationship(
        back_populates="patient",
        foreign_keys=lambda: [
            _typed_fact_column("Observation", "hospital_id"),
            _typed_fact_column("Observation", "patient_id"),
        ],
        primaryjoin=lambda: (
            (
                foreign(_typed_fact_column("Observation", "hospital_id"))
                == Patient.hospital_id
            )
            & (
                foreign(_typed_fact_column("Observation", "patient_id"))
                == Patient.id
            )
        ),
        overlaps="hospital,patient,observations",
    )
    medication_statements: Mapped[list["MedicationStatement"]] = relationship(
        back_populates="patient",
        foreign_keys=lambda: [
            _typed_fact_column("MedicationStatement", "hospital_id"),
            _typed_fact_column("MedicationStatement", "patient_id"),
        ],
        primaryjoin=lambda: (
            (
                foreign(_typed_fact_column("MedicationStatement", "hospital_id"))
                == Patient.hospital_id
            )
            & (
                foreign(_typed_fact_column("MedicationStatement", "patient_id"))
                == Patient.id
            )
        ),
        overlaps="hospital,patient,medication_statements",
    )
    merged_into: Mapped["Patient | None"] = relationship(
        "Patient",
        foreign_keys=lambda: [Patient.merged_into_patient_id],
        remote_side=lambda: [Patient.id],
        primaryjoin=lambda: (
            (foreign(Patient.merged_into_patient_id) == remote(Patient.id))
            & (Patient.hospital_id == remote(Patient.hospital_id))
        ),
        passive_deletes=True,
    )
