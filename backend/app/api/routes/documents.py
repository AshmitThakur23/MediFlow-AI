from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import (
    AuthorizationContext,
    require_patient_object_access,
    require_roles,
)
from app.models.document_extraction import DocumentExtraction
from app.models.document_extraction_correction import DocumentExtractionCorrection
from app.models.document_page import DocumentPage
from app.models.document_region import DocumentRegion
from app.models.encounter import Encounter
from app.models.hospital_user import HospitalUser
from app.models.medical_document import MedicalDocument
from app.models.patient import Patient


router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
}


class DocumentCreateRequest(BaseModel):
    patient_id: UUID
    encounter_id: UUID | None = None
    document_type: str = Field(min_length=1, max_length=64)
    original_name: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=1, max_length=128)
    object_uri: str = Field(min_length=1, max_length=2048)
    sha256: str | None = Field(default=None, min_length=64, max_length=64)
    document_date: date | None = None
    issuing_source: str | None = Field(default=None, max_length=255)
    page_count: int | None = Field(default=None, ge=1)
    processing_status: str = "uploaded"
    retention_status: str = "active"


class DocumentResponse(BaseModel):
    id: UUID
    hospital_id: UUID
    patient_id: UUID
    encounter_id: UUID | None
    document_type: str
    original_name: str
    mime_type: str
    object_uri: str
    sha256: str | None
    document_date: date | None
    upload_date: datetime
    issuing_source: str | None
    page_count: int | None
    processing_status: str
    retention_status: str
    uploaded_by_hospital_user_id: UUID


class PageCreateRequest(BaseModel):
    page_number: int = Field(ge=1)
    width: float | None = Field(default=None, ge=0)
    height: float | None = Field(default=None, ge=0)
    text_source: str | None = None


class PageResponse(BaseModel):
    id: UUID
    hospital_id: UUID
    document_id: UUID
    page_number: int
    width: float | None
    height: float | None
    text_source: str | None


class RegionCreateRequest(BaseModel):
    region_type: str = Field(min_length=1, max_length=64)
    x: Decimal | None = Field(default=None, ge=0)
    y: Decimal | None = Field(default=None, ge=0)
    width: Decimal | None = Field(default=None, ge=0)
    height: Decimal | None = Field(default=None, ge=0)
    text: str | None = None
    confidence: Decimal | None = Field(default=None, ge=0, le=1)


class RegionResponse(BaseModel):
    id: UUID
    hospital_id: UUID
    document_page_id: UUID
    region_type: str
    x: Decimal | None
    y: Decimal | None
    width: Decimal | None
    height: Decimal | None
    text: str | None
    confidence: Decimal | None


class ExtractionCreateRequest(BaseModel):
    document_region_id: UUID | None = None
    field_name: str = Field(min_length=1)
    extracted_value: str | None = None
    normalized_value: str | None = None
    unit: str | None = None
    reference_range: str | None = None
    extraction_status: str = Field(min_length=1)
    confidence: Decimal | None = Field(default=None, ge=0, le=1)


class ExtractionResponse(BaseModel):
    id: UUID
    hospital_id: UUID
    document_id: UUID
    document_region_id: UUID | None
    field_name: str
    extracted_value: str | None
    normalized_value: str | None
    unit: str | None
    reference_range: str | None
    extraction_status: str
    confidence: Decimal | None
    reviewed_by_hospital_user_id: UUID | None
    reviewed_at: datetime | None


class CorrectionCreateRequest(BaseModel):
    previous_value: str | None = None
    corrected_value: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class CorrectionResponse(BaseModel):
    id: UUID
    hospital_id: UUID
    extraction_id: UUID
    corrected_by_hospital_user_id: UUID
    previous_value: str | None
    corrected_value: str
    reason: str
    corrected_at: datetime


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
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Encounter not found")
    if encounter.patient_id != patient_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Encounter does not belong to the patient")


def get_document(
    context: AuthorizationContext,
    document_id: UUID,
) -> MedicalDocument:
    document = context.db.scalar(
        select(MedicalDocument).where(
            MedicalDocument.hospital_id == context.hospital_id,
            MedicalDocument.id == document_id,
        )
    )
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    require_patient_object_access(context, document.patient_id)
    return document


@router.post("", response_model=DocumentResponse, status_code=201)
def create_document(
    request: DocumentCreateRequest,
    context: AuthorizationContext = Depends(require_roles("doctor", "staff")),
) -> DocumentResponse:
    if request.mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Unsupported document MIME type",
        )
    if request.sha256 is not None:
        try:
            int(request.sha256, 16)
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "SHA-256 must contain hexadecimal characters",
            ) from exc
    get_patient(context, request.patient_id)
    validate_encounter(context, request.encounter_id, request.patient_id)

    document = MedicalDocument(
        hospital_id=context.hospital_id,
        patient_id=request.patient_id,
        encounter_id=request.encounter_id,
        document_type=request.document_type,
        original_name=request.original_name,
        mime_type=request.mime_type,
        object_uri=request.object_uri,
        sha256=request.sha256.lower() if request.sha256 is not None else None,
        document_date=request.document_date,
        issuing_source=request.issuing_source,
        page_count=request.page_count,
        processing_status=request.processing_status,
        retention_status=request.retention_status,
        uploaded_by_hospital_user_id=context.assignment.id,
    )
    context.db.add(document)
    try:
        context.db.commit()
    except IntegrityError as exc:
        context.db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Document integrity constraint rejected the record") from exc
    context.db.refresh(document)
    return DocumentResponse.model_validate(document, from_attributes=True)


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    context: AuthorizationContext = Depends(require_roles("doctor", "staff")),
) -> list[DocumentResponse]:
    documents = context.db.scalars(
        select(MedicalDocument).where(
            MedicalDocument.hospital_id == context.hospital_id,
        )
    ).all()
    allowed = []
    for document in documents:
        try:
            require_patient_object_access(context, document.patient_id)
            allowed.append(document)
        except HTTPException as exc:
            if exc.status_code != status.HTTP_403_FORBIDDEN:
                raise
    return [
        DocumentResponse.model_validate(document, from_attributes=True)
        for document in allowed
    ]


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document_metadata(
    document_id: UUID,
    context: AuthorizationContext = Depends(require_roles("doctor", "staff")),
) -> DocumentResponse:
    document = get_document(context, document_id)
    return DocumentResponse.model_validate(document, from_attributes=True)


@router.post("/{document_id}/pages", response_model=PageResponse, status_code=201)
def create_document_page(
    document_id: UUID,
    request: PageCreateRequest,
    context: AuthorizationContext = Depends(require_roles("doctor", "staff")),
) -> PageResponse:
    document = get_document(context, document_id)
    page = DocumentPage(
        hospital_id=context.hospital_id,
        document_id=document.id,
        page_number=request.page_number,
        width=request.width,
        height=request.height,
        text_source=request.text_source,
    )
    context.db.add(page)
    try:
        context.db.commit()
    except IntegrityError as exc:
        context.db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Document page integrity constraint rejected the record") from exc
    context.db.refresh(page)
    return PageResponse.model_validate(page, from_attributes=True)


@router.get("/{document_id}/pages", response_model=list[PageResponse])
def list_document_pages(
    document_id: UUID,
    context: AuthorizationContext = Depends(require_roles("doctor", "staff")),
) -> list[PageResponse]:
    document = get_document(context, document_id)
    pages = context.db.scalars(
        select(DocumentPage).where(
            DocumentPage.hospital_id == context.hospital_id,
            DocumentPage.document_id == document.id,
        ).order_by(DocumentPage.page_number)
    ).all()
    return [PageResponse.model_validate(page, from_attributes=True) for page in pages]


@router.post("/{document_id}/pages/{page_id}/regions", response_model=RegionResponse, status_code=201)
def create_document_region(
    document_id: UUID,
    page_id: UUID,
    request: RegionCreateRequest,
    context: AuthorizationContext = Depends(require_roles("doctor", "staff")),
) -> RegionResponse:
    document = get_document(context, document_id)
    page = context.db.scalar(
        select(DocumentPage).where(
            DocumentPage.hospital_id == context.hospital_id,
            DocumentPage.document_id == document.id,
            DocumentPage.id == page_id,
        )
    )
    if page is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document page not found")
    region = DocumentRegion(
        hospital_id=context.hospital_id,
        document_page_id=page.id,
        region_type=request.region_type,
        x=request.x,
        y=request.y,
        width=request.width,
        height=request.height,
        text=request.text,
        confidence=request.confidence,
    )
    context.db.add(region)
    try:
        context.db.commit()
    except IntegrityError as exc:
        context.db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Document region integrity constraint rejected the record") from exc
    context.db.refresh(region)
    return RegionResponse.model_validate(region, from_attributes=True)


@router.post("/{document_id}/extractions", response_model=ExtractionResponse, status_code=201)
def create_extraction(
    document_id: UUID,
    request: ExtractionCreateRequest,
    context: AuthorizationContext = Depends(require_roles("doctor", "staff")),
) -> ExtractionResponse:
    document = get_document(context, document_id)
    if request.document_region_id is not None:
        region = context.db.scalar(
            select(DocumentRegion).where(
                DocumentRegion.hospital_id == context.hospital_id,
                DocumentRegion.id == request.document_region_id,
            )
        )
        if region is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Document region not found")
        page = context.db.scalar(
            select(DocumentPage).where(
                DocumentPage.hospital_id == context.hospital_id,
                DocumentPage.id == region.document_page_id,
            )
        )
        if page is None or page.document_id != document.id:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Extraction region does not belong to the document",
            )
    extraction = DocumentExtraction(
        hospital_id=context.hospital_id,
        document_id=document.id,
        document_region_id=request.document_region_id,
        field_name=request.field_name,
        extracted_value=request.extracted_value,
        normalized_value=request.normalized_value,
        unit=request.unit,
        reference_range=request.reference_range,
        extraction_status=request.extraction_status,
        confidence=request.confidence,
    )
    context.db.add(extraction)
    try:
        context.db.commit()
    except IntegrityError as exc:
        context.db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Document extraction integrity constraint rejected the record") from exc
    context.db.refresh(extraction)
    return ExtractionResponse.model_validate(extraction, from_attributes=True)


@router.get("/{document_id}/extractions", response_model=list[ExtractionResponse])
def list_extractions(
    document_id: UUID,
    context: AuthorizationContext = Depends(require_roles("doctor", "staff")),
) -> list[ExtractionResponse]:
    document = get_document(context, document_id)
    rows = context.db.scalars(
        select(DocumentExtraction).where(
            DocumentExtraction.hospital_id == context.hospital_id,
            DocumentExtraction.document_id == document.id,
        )
    ).all()
    return [
        ExtractionResponse.model_validate(row, from_attributes=True)
        for row in rows
    ]


@router.post("/{document_id}/extractions/{extraction_id}/corrections", response_model=CorrectionResponse, status_code=201)
def correct_extraction(
    document_id: UUID,
    extraction_id: UUID,
    request: CorrectionCreateRequest,
    context: AuthorizationContext = Depends(require_roles("doctor")),
) -> CorrectionResponse:
    document = get_document(context, document_id)
    extraction = context.db.scalar(
        select(DocumentExtraction).where(
            DocumentExtraction.hospital_id == context.hospital_id,
            DocumentExtraction.document_id == document.id,
            DocumentExtraction.id == extraction_id,
        )
    )
    if extraction is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Extraction not found")
    correction = DocumentExtractionCorrection(
        hospital_id=context.hospital_id,
        extraction_id=extraction.id,
        corrected_by_hospital_user_id=context.assignment.id,
        previous_value=request.previous_value,
        corrected_value=request.corrected_value,
        reason=request.reason,
        corrected_at=datetime.now(timezone.utc),
    )
    context.db.add(correction)
    try:
        context.db.commit()
    except IntegrityError as exc:
        context.db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Extraction correction integrity constraint rejected the record") from exc
    context.db.refresh(correction)
    return CorrectionResponse.model_validate(correction, from_attributes=True)
