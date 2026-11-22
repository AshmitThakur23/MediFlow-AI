from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import (
    AuthorizationContext,
    require_patient_object_access,
    require_roles,
)
from app.models.allergy_intolerance import AllergyIntolerance
from app.models.condition import Condition
from app.models.encounter import Encounter
from app.models.hospital_user import HospitalUser
from app.models.medication_statement import MedicationStatement
from app.models.observation import Observation
from app.models.patient import Patient
from app.models.provenance_record import ProvenanceRecord


router = APIRouter(tags=["clinical-history"])

SOURCE_TYPES = {
    "conversation",
    "document",
    "doctor_entry",
    "patient_statement",
    "import",
    "ai_draft",
    "prescription",
    "catalogue",
}
VERIFICATION_STATUSES = {"unverified", "reviewed", "verified", "disputed"}
ALLERGY_CRITICALITIES = {"low", "high", "unknown", "unable_to_assess"}


class ProvenanceCreateRequest(BaseModel):
    patient_id: UUID | None = None
    encounter_id: UUID | None = None
    source_type: str
    source_record_id: UUID | None = None
    author_hospital_user_id: UUID | None = None
    recorded_at: datetime
    source_at: datetime | None = None
    verification_status: str
    uncertainty: str = Field(min_length=1, max_length=24)
    confidence: Decimal | None = Field(default=None, ge=0, le=1)
    notes: str | None = None


class ProvenanceResponse(BaseModel):
    id: UUID
    hospital_id: UUID
    patient_id: UUID | None
    encounter_id: UUID | None
    source_type: str
    source_record_id: UUID | None
    author_hospital_user_id: UUID | None
    recorded_at: datetime
    source_at: datetime | None
    verification_status: str
    uncertainty: str
    confidence: Decimal | None
    notes: str | None


class ConditionCreateRequest(BaseModel):
    patient_id: UUID
    encounter_id: UUID | None = None
    provenance_id: UUID
    code_system: str | None = Field(default=None, max_length=64)
    code_value: str | None = Field(default=None, max_length=128)
    display_name: str = Field(min_length=1, max_length=255)
    status: str = Field(min_length=1, max_length=24)
    verification_status: str = Field(min_length=1, max_length=24)
    onset_at: datetime | None = None
    superseded_by_condition_id: UUID | None = None


class AllergyCreateRequest(BaseModel):
    patient_id: UUID
    encounter_id: UUID | None = None
    provenance_id: UUID
    substance: str = Field(min_length=1, max_length=255)
    reaction: str | None = None
    criticality: str | None = None
    status: str = Field(min_length=1, max_length=24)
    verification_status: str = Field(min_length=1, max_length=24)
    reported_at: datetime | None = None


class ObservationCreateRequest(BaseModel):
    patient_id: UUID
    encounter_id: UUID | None = None
    provenance_id: UUID
    observation_type: str = Field(min_length=1, max_length=64)
    test_name: str | None = Field(default=None, max_length=255)
    value_text: str | None = None
    value_numeric: Decimal | None = None
    unit: str | None = Field(default=None, max_length=64)
    reference_range: str | None = Field(default=None, max_length=128)
    reported_at: datetime | None = None


class MedicationCreateRequest(BaseModel):
    patient_id: UUID
    encounter_id: UUID | None = None
    provenance_id: UUID
    medicine_name: str = Field(min_length=1, max_length=255)
    catalogue_item_id: UUID | None = None
    statement_type: str = Field(min_length=1, max_length=32)
    status: str = Field(min_length=1, max_length=24)
    dose: str | None = Field(default=None, max_length=128)
    start_at: datetime | None = None
    end_at: datetime | None = None
    superseded_by_statement_id: UUID | None = None
    verification_status: str = Field(min_length=1, max_length=24)


class ProvenanceListItemResponse(ProvenanceResponse):
    pass


class ConditionResponse(BaseModel):
    id: UUID
    hospital_id: UUID
    patient_id: UUID
    encounter_id: UUID | None
    provenance_id: UUID
    code_system: str | None
    code_value: str | None
    display_name: str
    status: str
    verification_status: str
    onset_at: datetime | None
    superseded_by_condition_id: UUID | None
    recorded_at: datetime


class AllergyResponse(BaseModel):
    id: UUID
    hospital_id: UUID
    patient_id: UUID
    encounter_id: UUID | None
    provenance_id: UUID
    substance: str
    reaction: str | None
    criticality: str | None
    status: str
    verification_status: str
    reported_at: datetime | None
    recorded_at: datetime


class ObservationResponse(BaseModel):
    id: UUID
    hospital_id: UUID
    patient_id: UUID
    encounter_id: UUID | None
    provenance_id: UUID
    observation_type: str
    test_name: str | None
    value_text: str | None
    value_numeric: Decimal | None
    unit: str | None
    reference_range: str | None
    reported_at: datetime | None
    recorded_at: datetime


class MedicationResponse(BaseModel):
    id: UUID
    hospital_id: UUID
    patient_id: UUID
    encounter_id: UUID | None
    provenance_id: UUID
    medicine_name: str
    catalogue_item_id: UUID | None
    statement_type: str
    status: str
    dose: str | None
    start_at: datetime | None
    end_at: datetime | None
    superseded_by_statement_id: UUID | None
    verification_status: str
    recorded_at: datetime


def get_patient(
    context: AuthorizationContext,
    patient_id: UUID,
) -> Patient:
    require_patient_object_access(context, patient_id)
    patient = context.db.scalar(
        select(Patient).where(
            Patient.hospital_id == context.hospital_id,
            Patient.id == patient_id,
        )
    )
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    return patient


def validate_encounter(
    context: AuthorizationContext,
    encounter_id: UUID | None,
    patient_id: UUID,
) -> None:
    if encounter_id is None:
        return
    encounter = context.db.scalar(
        select(Encounter).where(
            Encounter.hospital_id == context.hospital_id,
            Encounter.id == encounter_id,
        )
    )
    if encounter is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Encounter not found in the requested hospital",
        )
    if encounter.patient_id != patient_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Encounter does not belong to the patient",
        )


def validate_provenance(
    context: AuthorizationContext,
    provenance_id: UUID,
    patient_id: UUID,
) -> ProvenanceRecord:
    provenance = context.db.scalar(
        select(ProvenanceRecord).where(
            ProvenanceRecord.hospital_id == context.hospital_id,
            ProvenanceRecord.id == provenance_id,
        )
    )
    if provenance is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Provenance record not found in the requested hospital",
        )
    if provenance.patient_id is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Typed clinical facts require patient-linked provenance",
        )
    if provenance.patient_id != patient_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Provenance record does not belong to the patient",
        )
    if provenance.encounter_id is not None:
        validate_encounter(context, provenance.encounter_id, patient_id)
    return provenance


def validate_author(
    context: AuthorizationContext,
    author_hospital_user_id: UUID | None,
) -> None:
    if author_hospital_user_id is None:
        return
    author = context.db.scalar(
        select(HospitalUser).where(
            HospitalUser.hospital_id == context.hospital_id,
            HospitalUser.id == author_hospital_user_id,
        )
    )
    if author is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Author assignment not found in the requested hospital",
        )


@router.post("/provenance", response_model=ProvenanceResponse, status_code=201)
def create_provenance(
    request: ProvenanceCreateRequest,
    context: AuthorizationContext = Depends(require_roles("doctor", "staff")),
) -> ProvenanceResponse:
    if request.source_type not in SOURCE_TYPES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid source type")
    if request.verification_status not in VERIFICATION_STATUSES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid verification status")
    if request.encounter_id is not None and request.patient_id is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Encounter-linked provenance requires a patient",
        )
    if request.patient_id is not None:
        get_patient(context, request.patient_id)
    validate_encounter(context, request.encounter_id, request.patient_id) if request.patient_id is not None else None
    validate_author(context, request.author_hospital_user_id)

    record = ProvenanceRecord(
        hospital_id=context.hospital_id,
        patient_id=request.patient_id,
        encounter_id=request.encounter_id,
        source_type=request.source_type,
        source_record_id=request.source_record_id,
        author_hospital_user_id=request.author_hospital_user_id,
        recorded_at=request.recorded_at,
        source_at=request.source_at,
        verification_status=request.verification_status,
        uncertainty=request.uncertainty,
        confidence=request.confidence,
        notes=request.notes,
    )
    context.db.add(record)
    try:
        context.db.commit()
    except IntegrityError as exc:
        context.db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Provenance integrity constraint rejected the record") from exc
    context.db.refresh(record)
    return to_provenance_response(record)


@router.get("/provenance", response_model=list[ProvenanceListItemResponse])
def list_provenance(
    patient_id: UUID | None = Query(default=None),
    context: AuthorizationContext = Depends(require_roles("doctor", "staff")),
) -> list[ProvenanceListItemResponse]:
    statement = select(ProvenanceRecord).where(
        ProvenanceRecord.hospital_id == context.hospital_id,
    )
    if patient_id is not None:
        get_patient(context, patient_id)
        statement = statement.where(ProvenanceRecord.patient_id == patient_id)
    records = context.db.scalars(statement).all()
    return [to_provenance_response(record) for record in records]


@router.post("/conditions", response_model=ConditionResponse, status_code=201)
def create_condition(
    request: ConditionCreateRequest,
    context: AuthorizationContext = Depends(require_roles("doctor", "staff")),
) -> ConditionResponse:
    get_patient(context, request.patient_id)
    validate_encounter(context, request.encounter_id, request.patient_id)
    validate_provenance(context, request.provenance_id, request.patient_id)
    if request.superseded_by_condition_id is not None:
        target = context.db.scalar(
            select(Condition).where(
                Condition.hospital_id == context.hospital_id,
                Condition.id == request.superseded_by_condition_id,
            )
        )
        if target is None or target.patient_id != request.patient_id:
            raise HTTPException(status.HTTP_409_CONFLICT, "Condition supersession must use a same-hospital, same-patient record")
    row = Condition(
        hospital_id=context.hospital_id,
        patient_id=request.patient_id,
        encounter_id=request.encounter_id,
        provenance_id=request.provenance_id,
        code_system=request.code_system,
        code_value=request.code_value,
        display_name=request.display_name,
        status=request.status,
        verification_status=request.verification_status,
        onset_at=request.onset_at,
        superseded_by_condition_id=request.superseded_by_condition_id,
    )
    return persist_typed(context, row, ConditionResponse)


@router.get("/conditions", response_model=list[ConditionResponse])
def list_conditions(
    patient_id: UUID | None = Query(default=None),
    context: AuthorizationContext = Depends(require_roles("doctor", "staff")),
) -> list[ConditionResponse]:
    statement = select(Condition).where(
        Condition.hospital_id == context.hospital_id,
    )
    if patient_id is not None:
        get_patient(context, patient_id)
        statement = statement.where(Condition.patient_id == patient_id)
    rows = context.db.scalars(statement).all()
    return [to_condition_response(row) for row in rows]


@router.post("/allergies", response_model=AllergyResponse, status_code=201)
def create_allergy(
    request: AllergyCreateRequest,
    context: AuthorizationContext = Depends(require_roles("doctor", "staff")),
) -> AllergyResponse:
    get_patient(context, request.patient_id)
    validate_encounter(context, request.encounter_id, request.patient_id)
    validate_provenance(context, request.provenance_id, request.patient_id)
    if request.criticality is not None and request.criticality not in ALLERGY_CRITICALITIES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid allergy criticality")
    row = AllergyIntolerance(
        hospital_id=context.hospital_id,
        patient_id=request.patient_id,
        encounter_id=request.encounter_id,
        provenance_id=request.provenance_id,
        substance=request.substance,
        reaction=request.reaction,
        criticality=request.criticality,
        status=request.status,
        verification_status=request.verification_status,
        reported_at=request.reported_at,
    )
    return persist_typed(context, row, AllergyResponse)


@router.get("/allergies", response_model=list[AllergyResponse])
def list_allergies(
    patient_id: UUID | None = Query(default=None),
    context: AuthorizationContext = Depends(require_roles("doctor", "staff")),
) -> list[AllergyResponse]:
    statement = select(AllergyIntolerance).where(
        AllergyIntolerance.hospital_id == context.hospital_id,
    )
    if patient_id is not None:
        get_patient(context, patient_id)
        statement = statement.where(AllergyIntolerance.patient_id == patient_id)
    rows = context.db.scalars(statement).all()
    return [to_allergy_response(row) for row in rows]


@router.post("/observations", response_model=ObservationResponse, status_code=201)
def create_observation(
    request: ObservationCreateRequest,
    context: AuthorizationContext = Depends(require_roles("doctor", "staff")),
) -> ObservationResponse:
    get_patient(context, request.patient_id)
    validate_encounter(context, request.encounter_id, request.patient_id)
    validate_provenance(context, request.provenance_id, request.patient_id)
    if request.value_text is None and request.value_numeric is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Observation requires text or numeric value")
    row = Observation(
        hospital_id=context.hospital_id,
        patient_id=request.patient_id,
        encounter_id=request.encounter_id,
        provenance_id=request.provenance_id,
        observation_type=request.observation_type,
        test_name=request.test_name,
        value_text=request.value_text,
        value_numeric=request.value_numeric,
        unit=request.unit,
        reference_range=request.reference_range,
        reported_at=request.reported_at,
    )
    return persist_typed(context, row, ObservationResponse)


@router.get("/observations", response_model=list[ObservationResponse])
def list_observations(
    patient_id: UUID | None = Query(default=None),
    context: AuthorizationContext = Depends(require_roles("doctor", "staff")),
) -> list[ObservationResponse]:
    statement = select(Observation).where(
        Observation.hospital_id == context.hospital_id,
    )
    if patient_id is not None:
        get_patient(context, patient_id)
        statement = statement.where(Observation.patient_id == patient_id)
    rows = context.db.scalars(statement).all()
    return [to_observation_response(row) for row in rows]


@router.post("/medications", response_model=MedicationResponse, status_code=201)
def create_medication(
    request: MedicationCreateRequest,
    context: AuthorizationContext = Depends(require_roles("doctor", "staff")),
) -> MedicationResponse:
    get_patient(context, request.patient_id)
    validate_encounter(context, request.encounter_id, request.patient_id)
    validate_provenance(context, request.provenance_id, request.patient_id)
    if request.start_at is not None and request.end_at is not None and request.end_at < request.start_at:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Medication end cannot precede start")
    if request.superseded_by_statement_id is not None:
        target = context.db.scalar(
            select(MedicationStatement).where(
                MedicationStatement.hospital_id == context.hospital_id,
                MedicationStatement.id == request.superseded_by_statement_id,
            )
        )
        if target is None or target.patient_id != request.patient_id:
            raise HTTPException(status.HTTP_409_CONFLICT, "Medication supersession must use a same-hospital, same-patient record")
    row = MedicationStatement(
        hospital_id=context.hospital_id,
        patient_id=request.patient_id,
        encounter_id=request.encounter_id,
        provenance_id=request.provenance_id,
        medicine_name=request.medicine_name,
        catalogue_item_id=request.catalogue_item_id,
        statement_type=request.statement_type,
        status=request.status,
        dose=request.dose,
        start_at=request.start_at,
        end_at=request.end_at,
        superseded_by_statement_id=request.superseded_by_statement_id,
        verification_status=request.verification_status,
    )
    return persist_typed(context, row, MedicationResponse)


@router.get("/medications", response_model=list[MedicationResponse])
def list_medications(
    patient_id: UUID | None = Query(default=None),
    context: AuthorizationContext = Depends(require_roles("doctor", "staff")),
) -> list[MedicationResponse]:
    statement = select(MedicationStatement).where(
        MedicationStatement.hospital_id == context.hospital_id,
    )
    if patient_id is not None:
        get_patient(context, patient_id)
        statement = statement.where(
            MedicationStatement.patient_id == patient_id
        )
    rows = context.db.scalars(statement).all()
    return [to_medication_response(row) for row in rows]


def persist_typed(context, row, response_type):
    context.db.add(row)
    try:
        context.db.commit()
    except IntegrityError as exc:
        context.db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Clinical fact integrity constraint rejected the record") from exc
    context.db.refresh(row)
    if isinstance(row, Condition):
        return to_condition_response(row)
    if isinstance(row, AllergyIntolerance):
        return to_allergy_response(row)
    if isinstance(row, Observation):
        return to_observation_response(row)
    if isinstance(row, MedicationStatement):
        return to_medication_response(row)
    raise RuntimeError("Unsupported typed clinical fact")


def to_provenance_response(record: ProvenanceRecord) -> ProvenanceResponse:
    return ProvenanceResponse(
        id=record.id,
        hospital_id=record.hospital_id,
        patient_id=record.patient_id,
        encounter_id=record.encounter_id,
        source_type=record.source_type,
        source_record_id=record.source_record_id,
        author_hospital_user_id=record.author_hospital_user_id,
        recorded_at=record.recorded_at,
        source_at=record.source_at,
        verification_status=record.verification_status,
        uncertainty=record.uncertainty,
        confidence=record.confidence,
        notes=record.notes,
    )


def to_condition_response(row: Condition) -> ConditionResponse:
    return ConditionResponse.model_validate(row, from_attributes=True)


def to_allergy_response(row: AllergyIntolerance) -> AllergyResponse:
    return AllergyResponse.model_validate(row, from_attributes=True)


def to_observation_response(row: Observation) -> ObservationResponse:
    return ObservationResponse.model_validate(row, from_attributes=True)


def to_medication_response(row: MedicationStatement) -> MedicationResponse:
    return MedicationResponse.model_validate(row, from_attributes=True)
