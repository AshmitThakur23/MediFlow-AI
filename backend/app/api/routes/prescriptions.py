from datetime import datetime, timezone
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
from app.models.dispensing_record import DispensingRecord
from app.models.encounter import Encounter
from app.models.hospital_user import HospitalUser
from app.models.medication_statement import MedicationStatement
from app.models.medicine_catalogue_item import MedicineCatalogueItem
from app.models.patient import Patient
from app.models.prescription_draft import PrescriptionDraft
from app.models.prescription_draft_line import PrescriptionDraftLine
from app.models.prescription_line import PrescriptionLine
from app.models.signed_prescription import SignedPrescription


router = APIRouter(tags=["medicines-and-prescriptions"])


class CatalogueCreateRequest(BaseModel):
    catalogue_name: str = Field(min_length=1, max_length=128)
    catalogue_version: str = Field(min_length=1, max_length=64)
    generic_name: str = Field(min_length=1, max_length=255)
    brand_name: str | None = None
    active_ingredient: str | None = None
    manufacturer: str | None = None
    strength: str | None = None
    dosage_form: str | None = None
    route: str | None = None
    prescribing_information: str | None = None
    source_name: str = Field(min_length=1, max_length=255)
    source_uri: str | None = Field(default=None, max_length=2048)
    source_updated_at: datetime | None = None


class CatalogueResponse(BaseModel):
    id: UUID
    catalogue_name: str
    catalogue_version: str
    generic_name: str
    brand_name: str | None
    active_ingredient: str | None
    manufacturer: str | None
    strength: str | None
    dosage_form: str | None
    route: str | None
    prescribing_information: str | None
    source_name: str
    source_uri: str | None
    source_updated_at: datetime | None
    status: str


class DraftLineRequest(BaseModel):
    catalogue_item_id: UUID | None = None
    medicine_name: str = Field(min_length=1)
    strength: str | None = None
    dose: str | None = None
    route: str | None = None
    frequency: str | None = None
    duration: str | None = None
    quantity: str | None = None
    instructions: str | None = None


class DraftCreateRequest(BaseModel):
    patient_id: UUID
    encounter_id: UUID
    lines: list[DraftLineRequest] = Field(min_length=1)


class DraftApproveRequest(BaseModel):
    approved: bool


class DraftLineResponse(BaseModel):
    id: UUID
    catalogue_item_id: UUID | None
    medicine_name: str
    strength: str | None
    dose: str | None
    route: str | None
    frequency: str | None
    duration: str | None
    quantity: str | None
    instructions: str | None


class DraftResponse(BaseModel):
    id: UUID
    hospital_id: UUID
    patient_id: UUID
    encounter_id: UUID
    created_by_hospital_user_id: UUID
    status: str
    created_at: datetime
    lines: list[DraftLineResponse]
    safety_warnings: list[str]


class SignPrescriptionRequest(BaseModel):
    signature_reference: str | None = Field(default=None, max_length=255)


class PrescriptionLineResponse(BaseModel):
    id: UUID
    catalogue_item_id: UUID | None
    medicine_name: str
    strength: str | None
    dose: str | None
    route: str | None
    frequency: str | None
    duration: str | None
    quantity: str | None
    instructions: str | None


class PrescriptionResponse(BaseModel):
    id: UUID
    hospital_id: UUID
    patient_id: UUID
    encounter_id: UUID
    draft_id: UUID
    prescribing_hospital_user_id: UUID
    signed_at: datetime
    status: str
    signature_reference: str | None
    lines: list[PrescriptionLineResponse]


class PharmacyPrescriptionResponse(BaseModel):
    prescription_id: UUID
    patient_id: UUID
    prescriber_hospital_user_id: UUID
    signed_at: datetime
    status: str
    lines: list[PrescriptionLineResponse]


class DispensingCreateRequest(BaseModel):
    prescription_id: UUID


class DispensingResponse(BaseModel):
    id: UUID
    hospital_id: UUID
    patient_id: UUID
    prescription_id: UUID
    pharmacist_hospital_user_id: UUID
    status: str
    substitution_allowed: bool
    substitution_text: str | None
    clarification_text: str | None
    dispensed_at: datetime | None


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
    encounter_id: UUID,
    patient_id: UUID,
) -> Encounter:
    encounter = context.db.scalar(
        select(Encounter).where(
            Encounter.hospital_id == context.hospital_id,
            Encounter.id == encounter_id,
        )
    )
    if encounter is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Encounter not found")
    if encounter.patient_id != patient_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Encounter does not belong to the patient")
    return encounter


def validate_catalogue_line(
    context: AuthorizationContext,
    line: DraftLineRequest,
) -> MedicineCatalogueItem | None:
    if line.catalogue_item_id is None:
        return None
    item = context.db.scalar(
        select(MedicineCatalogueItem).where(
            MedicineCatalogueItem.id == line.catalogue_item_id,
            MedicineCatalogueItem.status == "active",
        )
    )
    if item is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Active catalogue item not found",
        )
    return item


def get_safety_warnings(
    context: AuthorizationContext,
    patient_id: UUID,
    lines: list[DraftLineRequest],
) -> list[str]:
    warnings: list[str] = []
    names = [
        line.medicine_name.strip().lower()
        for line in lines
        if line.medicine_name.strip()
    ]

    allergies = context.db.scalars(
        select(AllergyIntolerance).where(
            AllergyIntolerance.hospital_id == context.hospital_id,
            AllergyIntolerance.patient_id == patient_id,
        )
    ).all()
    for allergy in allergies:
        allergy_name = allergy.substance.strip().lower()
        if allergy_name and any(
            allergy_name in medicine_name or medicine_name in allergy_name
            for medicine_name in names
        ):
            warnings.append(
                f"Review possible documented allergy match: {allergy.substance}"
            )

    statements = context.db.scalars(
        select(MedicationStatement).where(
            MedicationStatement.hospital_id == context.hospital_id,
            MedicationStatement.patient_id == patient_id,
            MedicationStatement.status == "active",
        )
    ).all()
    existing_names = {
        statement.medicine_name.strip().lower()
        for statement in statements
        if statement.medicine_name.strip()
    }
    for medicine_name in names:
        if medicine_name in existing_names:
            warnings.append(
                f"Review possible duplicate therapy: {medicine_name}"
            )

    return sorted(set(warnings))


@router.post("/catalogue/items", response_model=CatalogueResponse, status_code=201)
def create_catalogue_item(
    request: CatalogueCreateRequest,
    context: AuthorizationContext = Depends(require_roles("doctor", "staff")),
) -> CatalogueResponse:
    item = MedicineCatalogueItem(
        catalogue_name=request.catalogue_name,
        catalogue_version=request.catalogue_version,
        generic_name=request.generic_name,
        brand_name=request.brand_name,
        active_ingredient=request.active_ingredient,
        manufacturer=request.manufacturer,
        strength=request.strength,
        dosage_form=request.dosage_form,
        route=request.route,
        prescribing_information=request.prescribing_information,
        source_name=request.source_name,
        source_uri=request.source_uri,
        source_updated_at=request.source_updated_at,
        status="active",
    )
    context.db.add(item)
    try:
        context.db.commit()
    except IntegrityError as exc:
        context.db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Catalogue item could not be created") from exc
    context.db.refresh(item)
    return to_catalogue_response(item)


@router.get("/catalogue/items", response_model=list[CatalogueResponse])
def search_catalogue(
    q: str | None = Query(default=None, min_length=1, max_length=255),
    context: AuthorizationContext = Depends(
        require_roles("doctor", "staff", "pharmacist")
    ),
) -> list[CatalogueResponse]:
    statement = select(MedicineCatalogueItem).where(
        MedicineCatalogueItem.status == "active",
    )
    if q:
        pattern = f"%{q}%"
        statement = statement.where(
            (MedicineCatalogueItem.generic_name.ilike(pattern))
            | (MedicineCatalogueItem.brand_name.ilike(pattern))
        )
    items = context.db.scalars(statement.limit(100)).all()
    return [to_catalogue_response(item) for item in items]


@router.post("/prescription-drafts", response_model=DraftResponse, status_code=201)
def create_draft(
    request: DraftCreateRequest,
    context: AuthorizationContext = Depends(require_roles("doctor")),
) -> DraftResponse:
    get_patient(context, request.patient_id)
    validate_encounter(context, request.encounter_id, request.patient_id)
    for line in request.lines:
        validate_catalogue_line(context, line)

    draft = PrescriptionDraft(
        hospital_id=context.hospital_id,
        patient_id=request.patient_id,
        encounter_id=request.encounter_id,
        created_by_hospital_user_id=context.assignment.id,
        status="draft",
    )
    context.db.add(draft)
    context.db.flush()
    for line in request.lines:
        context.db.add(
            PrescriptionDraftLine(
                hospital_id=context.hospital_id,
                draft_id=draft.id,
                catalogue_item_id=line.catalogue_item_id,
                medicine_name=line.medicine_name,
                strength=line.strength,
                dose=line.dose,
                route=line.route,
                frequency=line.frequency,
                duration=line.duration,
                quantity=line.quantity,
                instructions=line.instructions,
            )
        )
    try:
        context.db.commit()
    except IntegrityError as exc:
        context.db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Prescription draft integrity was rejected") from exc
    context.db.refresh(draft)
    draft_lines = context.db.scalars(
        select(PrescriptionDraftLine).where(
            PrescriptionDraftLine.hospital_id == context.hospital_id,
            PrescriptionDraftLine.draft_id == draft.id,
        )
    ).all()
    warnings = get_safety_warnings(context, request.patient_id, request.lines)
    return to_draft_response(draft, draft_lines, warnings)


@router.get("/prescription-drafts/{draft_id}", response_model=DraftResponse)
def get_draft(
    draft_id: UUID,
    context: AuthorizationContext = Depends(require_roles("doctor", "staff")),
) -> DraftResponse:
    draft = context.db.scalar(
        select(PrescriptionDraft).where(
            PrescriptionDraft.hospital_id == context.hospital_id,
            PrescriptionDraft.id == draft_id,
        )
    )
    if draft is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Prescription draft not found")
    require_patient_object_access(context, draft.patient_id)
    lines = context.db.scalars(
        select(PrescriptionDraftLine).where(
            PrescriptionDraftLine.hospital_id == context.hospital_id,
            PrescriptionDraftLine.draft_id == draft.id,
        )
    ).all()
    request_lines = [
        DraftLineRequest(
            catalogue_item_id=line.catalogue_item_id,
            medicine_name=line.medicine_name,
            strength=line.strength,
            dose=line.dose,
            route=line.route,
            frequency=line.frequency,
            duration=line.duration,
            quantity=line.quantity,
            instructions=line.instructions,
        )
        for line in lines
    ]
    return to_draft_response(
        draft,
        lines,
        get_safety_warnings(context, draft.patient_id, request_lines),
    )


@router.patch("/prescription-drafts/{draft_id}/approval", response_model=DraftResponse)
def approve_draft(
    draft_id: UUID,
    request: DraftApproveRequest,
    context: AuthorizationContext = Depends(require_roles("doctor")),
) -> DraftResponse:
    draft = context.db.scalar(
        select(PrescriptionDraft).where(
            PrescriptionDraft.hospital_id == context.hospital_id,
            PrescriptionDraft.id == draft_id,
        )
    )
    if draft is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Prescription draft not found")
    require_patient_object_access(context, draft.patient_id)
    if draft.status not in {"draft"}:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only an existing draft may be approved or rejected")
    draft.status = "approved" if request.approved else "cancelled"
    context.db.commit()
    context.db.refresh(draft)
    lines = context.db.scalars(
        select(PrescriptionDraftLine).where(
            PrescriptionDraftLine.hospital_id == context.hospital_id,
            PrescriptionDraftLine.draft_id == draft.id,
        )
    ).all()
    return to_draft_response(draft, lines, [])


@router.post("/prescriptions", response_model=PrescriptionResponse, status_code=201)
def sign_prescription(
    draft_id: UUID = Query(),
    request: SignPrescriptionRequest | None = None,
    context: AuthorizationContext = Depends(require_roles("doctor")),
) -> PrescriptionResponse:
    if request is None:
        request = SignPrescriptionRequest()
    draft = context.db.scalar(
        select(PrescriptionDraft).where(
            PrescriptionDraft.hospital_id == context.hospital_id,
            PrescriptionDraft.id == draft_id,
        )
    )
    if draft is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Prescription draft not found")
    require_patient_object_access(context, draft.patient_id)
    if draft.status != "approved":
        raise HTTPException(status.HTTP_409_CONFLICT, "Only an approved draft may be signed")

    draft_lines = context.db.scalars(
        select(PrescriptionDraftLine).where(
            PrescriptionDraftLine.hospital_id == context.hospital_id,
            PrescriptionDraftLine.draft_id == draft.id,
        )
    ).all()
    prescription = SignedPrescription(
        hospital_id=context.hospital_id,
        patient_id=draft.patient_id,
        encounter_id=draft.encounter_id,
        draft_id=draft.id,
        prescribing_hospital_user_id=context.assignment.id,
        signed_at=datetime.now(tz=timezone.utc),
        status="signed",
        signature_reference=request.signature_reference,
    )
    context.db.add(prescription)
    context.db.flush()
    for line in draft_lines:
        context.db.add(
            PrescriptionLine(
                hospital_id=context.hospital_id,
                prescription_id=prescription.id,
                catalogue_item_id=line.catalogue_item_id,
                medicine_name=line.medicine_name,
                strength=line.strength,
                dose=line.dose,
                route=line.route,
                frequency=line.frequency,
                duration=line.duration,
                quantity=line.quantity,
                instructions=line.instructions,
            )
        )
    try:
        context.db.commit()
    except IntegrityError as exc:
        context.db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Signed prescription integrity was rejected") from exc
    context.db.refresh(prescription)
    lines = context.db.scalars(
        select(PrescriptionLine).where(
            PrescriptionLine.hospital_id == context.hospital_id,
            PrescriptionLine.prescription_id == prescription.id,
        )
    ).all()
    return to_prescription_response(prescription, lines)


@router.get("/pharmacy/prescriptions/{prescription_id}", response_model=PharmacyPrescriptionResponse)
def pharmacy_prescription_view(
    prescription_id: UUID,
    context: AuthorizationContext = Depends(require_roles("pharmacist")),
) -> PharmacyPrescriptionResponse:
    prescription = context.db.scalar(
        select(SignedPrescription).where(
            SignedPrescription.hospital_id == context.hospital_id,
            SignedPrescription.id == prescription_id,
        )
    )
    if prescription is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Prescription not found")
    require_patient_object_access(context, prescription.patient_id)
    lines = context.db.scalars(
        select(PrescriptionLine).where(
            PrescriptionLine.hospital_id == context.hospital_id,
            PrescriptionLine.prescription_id == prescription.id,
        )
    ).all()
    return PharmacyPrescriptionResponse(
        prescription_id=prescription.id,
        patient_id=prescription.patient_id,
        prescriber_hospital_user_id=prescription.prescribing_hospital_user_id,
        signed_at=prescription.signed_at,
        status=prescription.status,
        lines=[to_prescription_line_response(line) for line in lines],
    )


@router.post("/dispensing", response_model=DispensingResponse, status_code=201)
def create_dispensing_record(
    request: DispensingCreateRequest,
    context: AuthorizationContext = Depends(require_roles("pharmacist")),
) -> DispensingResponse:
    prescription = context.db.scalar(
        select(SignedPrescription).where(
            SignedPrescription.hospital_id == context.hospital_id,
            SignedPrescription.id == request.prescription_id,
        )
    )
    if prescription is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Prescription not found")
    require_patient_object_access(context, prescription.patient_id)
    record = DispensingRecord(
        hospital_id=context.hospital_id,
        patient_id=prescription.patient_id,
        prescription_id=prescription.id,
        pharmacist_hospital_user_id=context.assignment.id,
        status="viewed",
        substitution_allowed=False,
    )
    context.db.add(record)
    try:
        context.db.commit()
    except IntegrityError as exc:
        context.db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Dispensing record integrity was rejected") from exc
    context.db.refresh(record)
    return to_dispensing_response(record)


def to_catalogue_response(item: MedicineCatalogueItem) -> CatalogueResponse:
    return CatalogueResponse.model_validate(item, from_attributes=True)


def to_draft_response(
    draft: PrescriptionDraft,
    lines,
    warnings: list[str],
) -> DraftResponse:
    return DraftResponse(
        id=draft.id,
        hospital_id=draft.hospital_id,
        patient_id=draft.patient_id,
        encounter_id=draft.encounter_id,
        created_by_hospital_user_id=draft.created_by_hospital_user_id,
        status=draft.status,
        created_at=draft.created_at,
        lines=[
            DraftLineResponse.model_validate(line, from_attributes=True)
            for line in lines
        ],
        safety_warnings=warnings,
    )


def to_prescription_line_response(line: PrescriptionLine) -> PrescriptionLineResponse:
    return PrescriptionLineResponse.model_validate(line, from_attributes=True)


def to_prescription_response(
    prescription: SignedPrescription,
    lines,
) -> PrescriptionResponse:
    return PrescriptionResponse(
        id=prescription.id,
        hospital_id=prescription.hospital_id,
        patient_id=prescription.patient_id,
        encounter_id=prescription.encounter_id,
        draft_id=prescription.draft_id,
        prescribing_hospital_user_id=prescription.prescribing_hospital_user_id,
        signed_at=prescription.signed_at,
        status=prescription.status,
        signature_reference=prescription.signature_reference,
        lines=[to_prescription_line_response(line) for line in lines],
    )


def to_dispensing_response(record: DispensingRecord) -> DispensingResponse:
    return DispensingResponse.model_validate(record, from_attributes=True)
