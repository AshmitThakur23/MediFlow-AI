from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
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


class Condition(Base):
    __tablename__ = "conditions"
    __table_args__ = (
        UniqueConstraint("hospital_id", "id", name="uq_conditions_hospital_id_id"),
        UniqueConstraint(
            "hospital_id",
            "id",
            "patient_id",
            name="uq_conditions_hospital_id_id_patient_id",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "patient_id"],
            ["patients.hospital_id", "patients.id"],
            name="fk_conditions_patient_same_hospital",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "encounter_id"],
            ["encounters.hospital_id", "encounters.id"],
            name="fk_conditions_encounter_same_hospital",
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
            name="fk_conditions_encounter_patient_same",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "provenance_id"],
            ["provenance_records.hospital_id", "provenance_records.id"],
            name="fk_conditions_provenance_same_hospital",
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
            name="fk_conditions_provenance_patient_same",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "superseded_by_condition_id", "patient_id"],
            ["conditions.hospital_id", "conditions.id", "conditions.patient_id"],
            name="fk_conditions_supersession_same_patient",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        Index(
            "ix_conditions_hospital_patient_recorded",
            "hospital_id",
            "patient_id",
            "recorded_at",
        ),
        Index(
            "ix_conditions_hospital_encounter_recorded",
            "hospital_id",
            "encounter_id",
            "recorded_at",
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
    code_system: Mapped[str | None] = mapped_column(String(64), nullable=True)
    code_value: Mapped[str | None] = mapped_column(String(128), nullable=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(24), nullable=False)
    onset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded_by_condition_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    hospital: Mapped["Hospital"] = relationship(back_populates="conditions")
    patient: Mapped["Patient"] = relationship(
        back_populates="conditions",
        foreign_keys=lambda: [Condition.hospital_id, Condition.patient_id],
        primaryjoin=lambda: (
            (foreign(Condition.hospital_id) == Patient.hospital_id)
            & (foreign(Condition.patient_id) == Patient.id)
        ),
        overlaps="hospital,conditions",
    )
    encounter: Mapped["Encounter | None"] = relationship(
        back_populates="conditions",
        foreign_keys=lambda: [Condition.hospital_id, Condition.encounter_id],
        primaryjoin=lambda: (
            (foreign(Condition.hospital_id) == Encounter.hospital_id)
            & (foreign(Condition.encounter_id) == Encounter.id)
        ),
        overlaps="hospital,patient,conditions",
    )
    provenance: Mapped["ProvenanceRecord"] = relationship(
        back_populates="conditions",
        foreign_keys=lambda: [Condition.hospital_id, Condition.provenance_id],
        primaryjoin=lambda: (
            (foreign(Condition.hospital_id) == ProvenanceRecord.hospital_id)
            & (foreign(Condition.provenance_id) == ProvenanceRecord.id)
        ),
        overlaps="hospital,patient,encounter,conditions",
    )
    superseded_by: Mapped["Condition | None"] = relationship(
        "Condition",
        foreign_keys=lambda: [
            Condition.hospital_id,
            Condition.superseded_by_condition_id,
            Condition.patient_id,
        ],
        primaryjoin=lambda: (
            (foreign(Condition.hospital_id) == Condition.hospital_id)
            & (
                foreign(Condition.superseded_by_condition_id)
                == Condition.id
            )
            & (foreign(Condition.patient_id) == Condition.patient_id)
        ),
        remote_side=lambda: [Condition.hospital_id, Condition.id, Condition.patient_id],
        uselist=False,
        overlaps="conditions,encounter,hospital,patient,provenance",
    )
