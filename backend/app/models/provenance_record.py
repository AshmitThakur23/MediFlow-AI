from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from app.db.base import Base
from app.models.encounter import Encounter
from app.models.hospital import Hospital
from app.models.hospital_user import HospitalUser
from app.models.patient import Patient


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


class ProvenanceRecord(Base):
    __tablename__ = "provenance_records"
    __table_args__ = (
        UniqueConstraint(
            "hospital_id",
            "id",
            name="uq_provenance_records_hospital_id_id",
        ),
        UniqueConstraint(
            "hospital_id",
            "id",
            "patient_id",
            name="uq_provenance_records_hospital_id_id_patient_id",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "patient_id"],
            ["patients.hospital_id", "patients.id"],
            name="fk_provenance_records_patient_same_hospital",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "encounter_id"],
            ["encounters.hospital_id", "encounters.id"],
            name="fk_provenance_records_encounter_same_hospital",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "encounter_id", "patient_id"],
            [
                "encounters.hospital_id",
                "encounters.id",
                "encounters.patient_id",
            ],
            name="fk_provenance_records_encounter_patient_same",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "author_hospital_user_id"],
            ["hospital_users.hospital_id", "hospital_users.id"],
            name="fk_provenance_records_author_same_hospital",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        Index(
            "ix_provenance_records_hospital_patient_recorded",
            "hospital_id",
            "patient_id",
            "recorded_at",
        ),
        Index(
            "ix_provenance_records_hospital_encounter_recorded",
            "hospital_id",
            "encounter_id",
            "recorded_at",
        ),
        Index(
            "ix_provenance_records_hospital_source_type_recorded",
            "hospital_id",
            "source_type",
            "recorded_at",
        ),
        CheckConstraint(
            "source_type IN ('conversation', 'document', 'doctor_entry', "
            "'patient_statement', 'import', 'ai_draft', 'prescription', "
            "'catalogue')",
            name="ck_provenance_records_source_type",
        ),
        CheckConstraint(
            "verification_status IN "
            "('unverified', 'reviewed', 'verified', 'disputed')",
            name="ck_provenance_records_verification_status",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_provenance_records_confidence",
        ),
        CheckConstraint(
            "encounter_id IS NULL OR patient_id IS NOT NULL",
            name="ck_provenance_records_encounter_requires_patient",
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
    patient_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )
    encounter_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )
    source_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    source_record_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )
    author_hospital_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    source_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    verification_status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
    )
    uncertainty: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
    )
    confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    hospital: Mapped["Hospital"] = relationship(
        back_populates="provenance_records",
        overlaps="patient,encounter,author_hospital_user",
    )
    patient: Mapped["Patient | None"] = relationship(
        back_populates="provenance_records",
        foreign_keys=lambda: [
            ProvenanceRecord.hospital_id,
            ProvenanceRecord.patient_id,
        ],
        primaryjoin=lambda: (
            (
                foreign(ProvenanceRecord.hospital_id)
                == Patient.hospital_id
            )
            & (foreign(ProvenanceRecord.patient_id) == Patient.id)
        ),
        overlaps="hospital,encounter,patient,provenance_records",
    )
    encounter: Mapped["Encounter | None"] = relationship(
        back_populates="provenance_records",
        foreign_keys=lambda: [
            ProvenanceRecord.hospital_id,
            ProvenanceRecord.encounter_id,
        ],
        primaryjoin=lambda: (
            (
                foreign(ProvenanceRecord.hospital_id)
                == Encounter.hospital_id
            )
            & (foreign(ProvenanceRecord.encounter_id) == Encounter.id)
        ),
        overlaps="hospital,patient,provenance_records",
    )
    author_hospital_user: Mapped["HospitalUser | None"] = relationship(
        back_populates="provenance_records",
        foreign_keys=lambda: [
            ProvenanceRecord.hospital_id,
            ProvenanceRecord.author_hospital_user_id,
        ],
        primaryjoin=lambda: (
            (
                foreign(ProvenanceRecord.hospital_id)
                == HospitalUser.hospital_id
            )
            & (
                foreign(ProvenanceRecord.author_hospital_user_id)
                == HospitalUser.id
            )
        ),
        overlaps="hospital,encounter,patient,provenance_records",
    )
    conditions: Mapped[list["Condition"]] = relationship(
        back_populates="provenance",
        foreign_keys=lambda: [
            _typed_fact_column("Condition", "hospital_id"),
            _typed_fact_column("Condition", "provenance_id"),
        ],
        primaryjoin=lambda: (
            (
                foreign(_typed_fact_column("Condition", "hospital_id"))
                == ProvenanceRecord.hospital_id
            )
            & (
                foreign(_typed_fact_column("Condition", "provenance_id"))
                == ProvenanceRecord.id
            )
        ),
        overlaps="hospital,patient,encounter,provenance,conditions",
    )
    allergy_intolerances: Mapped[list["AllergyIntolerance"]] = relationship(
        back_populates="provenance",
        foreign_keys=lambda: [
            _typed_fact_column("AllergyIntolerance", "hospital_id"),
            _typed_fact_column("AllergyIntolerance", "provenance_id"),
        ],
        primaryjoin=lambda: (
            (
                foreign(
                    _typed_fact_column("AllergyIntolerance", "hospital_id")
                )
                == ProvenanceRecord.hospital_id
            )
            & (
                foreign(
                    _typed_fact_column("AllergyIntolerance", "provenance_id")
                )
                == ProvenanceRecord.id
            )
        ),
        overlaps=(
            "hospital,patient,encounter,provenance,allergy_intolerances"
        ),
    )
    observations: Mapped[list["Observation"]] = relationship(
        back_populates="provenance",
        foreign_keys=lambda: [
            _typed_fact_column("Observation", "hospital_id"),
            _typed_fact_column("Observation", "provenance_id"),
        ],
        primaryjoin=lambda: (
            (
                foreign(_typed_fact_column("Observation", "hospital_id"))
                == ProvenanceRecord.hospital_id
            )
            & (
                foreign(_typed_fact_column("Observation", "provenance_id"))
                == ProvenanceRecord.id
            )
        ),
        overlaps="hospital,patient,encounter,provenance,observations",
    )
    medication_statements: Mapped[list["MedicationStatement"]] = relationship(
        back_populates="provenance",
        foreign_keys=lambda: [
            _typed_fact_column("MedicationStatement", "hospital_id"),
            _typed_fact_column("MedicationStatement", "provenance_id"),
        ],
        primaryjoin=lambda: (
            (
                foreign(_typed_fact_column("MedicationStatement", "hospital_id"))
                == ProvenanceRecord.hospital_id
            )
            & (
                foreign(_typed_fact_column("MedicationStatement", "provenance_id"))
                == ProvenanceRecord.id
            )
        ),
        overlaps=(
            "hospital,patient,encounter,provenance,medication_statements"
        ),
    )
