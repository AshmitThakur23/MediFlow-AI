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
from app.models.patient import Patient
from app.models.provenance_record import ProvenanceRecord


class Observation(Base):
    __tablename__ = "observations"
    __table_args__ = (
        UniqueConstraint("hospital_id", "id", name="uq_observations_hospital_id_id"),
        ForeignKeyConstraint(
            ["hospital_id", "patient_id"],
            ["patients.hospital_id", "patients.id"],
            name="fk_observations_patient_same_hospital",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "encounter_id"],
            ["encounters.hospital_id", "encounters.id"],
            name="fk_observations_encounter_same_hospital",
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
            name="fk_observations_encounter_patient_same",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "provenance_id"],
            ["provenance_records.hospital_id", "provenance_records.id"],
            name="fk_observations_provenance_same_hospital",
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
            name="fk_observations_provenance_patient_same",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        Index(
            "ix_observations_hospital_patient_reported",
            "hospital_id",
            "patient_id",
            "reported_at",
        ),
        Index(
            "ix_observations_hospital_encounter_reported",
            "hospital_id",
            "encounter_id",
            "reported_at",
        ),
        CheckConstraint(
            "value_text IS NOT NULL OR value_numeric IS NOT NULL",
            name="ck_observations_has_value",
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
    observation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    test_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_numeric: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reference_range: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    hospital: Mapped["Hospital"] = relationship(back_populates="observations")
    patient: Mapped["Patient"] = relationship(
        back_populates="observations",
        foreign_keys=lambda: [Observation.hospital_id, Observation.patient_id],
        primaryjoin=lambda: (
            (foreign(Observation.hospital_id) == Patient.hospital_id)
            & (foreign(Observation.patient_id) == Patient.id)
        ),
        overlaps="hospital,observations",
    )
    encounter: Mapped["Encounter | None"] = relationship(
        back_populates="observations",
        foreign_keys=lambda: [Observation.hospital_id, Observation.encounter_id],
        primaryjoin=lambda: (
            (foreign(Observation.hospital_id) == Encounter.hospital_id)
            & (foreign(Observation.encounter_id) == Encounter.id)
        ),
        overlaps="hospital,patient,observations",
    )
    provenance: Mapped["ProvenanceRecord"] = relationship(
        back_populates="observations",
        foreign_keys=lambda: [Observation.hospital_id, Observation.provenance_id],
        primaryjoin=lambda: (
            (foreign(Observation.hospital_id) == ProvenanceRecord.hospital_id)
            & (foreign(Observation.provenance_id) == ProvenanceRecord.id)
        ),
        overlaps="hospital,patient,encounter,observations",
    )
