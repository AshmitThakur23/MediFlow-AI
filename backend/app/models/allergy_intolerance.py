from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
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
from app.models.patient import Patient
from app.models.provenance_record import ProvenanceRecord


class AllergyIntolerance(Base):
    __tablename__ = "allergy_intolerances"
    __table_args__ = (
        UniqueConstraint(
            "hospital_id",
            "id",
            name="uq_allergy_intolerances_hospital_id_id",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "patient_id"],
            ["patients.hospital_id", "patients.id"],
            name="fk_allergy_intolerances_patient_same_hospital",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "encounter_id"],
            ["encounters.hospital_id", "encounters.id"],
            name="fk_allergy_intolerances_encounter_same_hospital",
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
            name="fk_allergy_intolerances_encounter_patient_same",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "provenance_id"],
            ["provenance_records.hospital_id", "provenance_records.id"],
            name="fk_allergy_intolerances_provenance_same_hospital",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "provenance_id", "patient_id"],
            [
                "provenance_records.hospital_id",
                "provenance_records.id",
                "provenance_records.patient_id",
            ],
            name="fk_allergy_intolerances_provenance_patient_same",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        Index(
            "ix_allergy_intolerances_hospital_patient_reported",
            "hospital_id",
            "patient_id",
            "reported_at",
        ),
        CheckConstraint(
            "criticality IN ('low', 'high', 'unknown', 'unable_to_assess')",
            name="ck_allergy_intolerances_criticality",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    hospital_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hospitals.id", ondelete="RESTRICT"),
        nullable=False,
    )
    patient_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    encounter_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    provenance_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    substance: Mapped[str] = mapped_column(String(255), nullable=False)
    reaction: Mapped[str | None] = mapped_column(Text, nullable=True)
    criticality: Mapped[str | None] = mapped_column(String(24), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(24), nullable=False)
    reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    hospital: Mapped["Hospital"] = relationship(back_populates="allergy_intolerances")
    patient: Mapped["Patient"] = relationship(
        back_populates="allergy_intolerances",
        foreign_keys=lambda: [
            AllergyIntolerance.hospital_id,
            AllergyIntolerance.patient_id,
        ],
        primaryjoin=lambda: (
            (foreign(AllergyIntolerance.hospital_id) == Patient.hospital_id)
            & (foreign(AllergyIntolerance.patient_id) == Patient.id)
        ),
        overlaps="hospital,allergy_intolerances",
    )
    encounter: Mapped["Encounter | None"] = relationship(
        back_populates="allergy_intolerances",
        foreign_keys=lambda: [
            AllergyIntolerance.hospital_id,
            AllergyIntolerance.encounter_id,
        ],
        primaryjoin=lambda: (
            (foreign(AllergyIntolerance.hospital_id) == Encounter.hospital_id)
            & (foreign(AllergyIntolerance.encounter_id) == Encounter.id)
        ),
        overlaps="hospital,patient,allergy_intolerances",
    )
    provenance: Mapped["ProvenanceRecord"] = relationship(
        back_populates="allergy_intolerances",
        foreign_keys=lambda: [
            AllergyIntolerance.hospital_id,
            AllergyIntolerance.provenance_id,
        ],
        primaryjoin=lambda: (
            (foreign(AllergyIntolerance.hospital_id) == ProvenanceRecord.hospital_id)
            & (foreign(AllergyIntolerance.provenance_id) == ProvenanceRecord.id)
        ),
        overlaps="hospital,patient,encounter,allergy_intolerances",
    )
