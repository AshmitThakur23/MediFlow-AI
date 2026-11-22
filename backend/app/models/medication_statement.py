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


class MedicationStatement(Base):
    __tablename__ = "medication_statements"
    __table_args__ = (
        UniqueConstraint(
            "hospital_id",
            "id",
            name="uq_medication_statements_hospital_id_id",
        ),
        UniqueConstraint(
            "hospital_id",
            "id",
            "patient_id",
            name="uq_medication_statements_hospital_id_id_patient_id",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "patient_id"],
            ["patients.hospital_id", "patients.id"],
            name="fk_medication_statements_patient_same_hospital",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "encounter_id"],
            ["encounters.hospital_id", "encounters.id"],
            name="fk_medication_statements_encounter_same_hospital",
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
            name="fk_medication_statements_encounter_patient_same",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "provenance_id"],
            ["provenance_records.hospital_id", "provenance_records.id"],
            name="fk_medication_statements_provenance_same_hospital",
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
            name="fk_medication_statements_provenance_patient_same",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["hospital_id", "superseded_by_statement_id", "patient_id"],
            [
                "medication_statements.hospital_id",
                "medication_statements.id",
                "medication_statements.patient_id",
            ],
            name="fk_medication_statements_supersession_same_patient",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        Index(
            "ix_medication_statements_hospital_patient_recorded",
            "hospital_id",
            "patient_id",
            "recorded_at",
        ),
        Index(
            "ix_medication_statements_hospital_encounter_recorded",
            "hospital_id",
            "encounter_id",
            "recorded_at",
        ),
        CheckConstraint(
            "end_at IS NULL OR start_at IS NULL OR end_at >= start_at",
            name="ck_medication_statements_date_order",
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
    medicine_name: Mapped[str] = mapped_column(String(255), nullable=False)
    catalogue_item_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("medicine_catalogue_items.id", ondelete="RESTRICT"),
        nullable=True,
    )
    statement_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    dose: Mapped[str | None] = mapped_column(String(128), nullable=True)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded_by_statement_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )
    verification_status: Mapped[str] = mapped_column(String(24), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    hospital: Mapped["Hospital"] = relationship(back_populates="medication_statements")
    patient: Mapped["Patient"] = relationship(
        back_populates="medication_statements",
        foreign_keys=lambda: [
            MedicationStatement.hospital_id,
            MedicationStatement.patient_id,
        ],
        primaryjoin=lambda: (
            (foreign(MedicationStatement.hospital_id) == Patient.hospital_id)
            & (foreign(MedicationStatement.patient_id) == Patient.id)
        ),
        overlaps="hospital,medication_statements",
    )
    encounter: Mapped["Encounter | None"] = relationship(
        back_populates="medication_statements",
        foreign_keys=lambda: [
            MedicationStatement.hospital_id,
            MedicationStatement.encounter_id,
        ],
        primaryjoin=lambda: (
            (foreign(MedicationStatement.hospital_id) == Encounter.hospital_id)
            & (foreign(MedicationStatement.encounter_id) == Encounter.id)
        ),
        overlaps="hospital,patient,medication_statements",
    )
    provenance: Mapped["ProvenanceRecord"] = relationship(
        back_populates="medication_statements",
        foreign_keys=lambda: [
            MedicationStatement.hospital_id,
            MedicationStatement.provenance_id,
        ],
        primaryjoin=lambda: (
            (foreign(MedicationStatement.hospital_id) == ProvenanceRecord.hospital_id)
            & (foreign(MedicationStatement.provenance_id) == ProvenanceRecord.id)
        ),
        overlaps="hospital,patient,encounter,medication_statements",
    )
    catalogue_item: Mapped["MedicineCatalogueItem | None"] = relationship(
        "MedicineCatalogueItem",
        back_populates="medication_statements",
    )
    superseded_by: Mapped["MedicationStatement | None"] = relationship(
        "MedicationStatement",
        foreign_keys=lambda: [
            MedicationStatement.hospital_id,
            MedicationStatement.superseded_by_statement_id,
            MedicationStatement.patient_id,
        ],
        primaryjoin=lambda: (
            (foreign(MedicationStatement.hospital_id) == MedicationStatement.hospital_id)
            & (
                foreign(MedicationStatement.superseded_by_statement_id)
                == MedicationStatement.id
            )
            & (foreign(MedicationStatement.patient_id) == MedicationStatement.patient_id)
        ),
        remote_side=lambda: [
            MedicationStatement.hospital_id,
            MedicationStatement.id,
            MedicationStatement.patient_id,
        ],
        uselist=False,
        overlaps=(
            "medication_statements,encounter,hospital,patient,provenance"
        ),
    )
