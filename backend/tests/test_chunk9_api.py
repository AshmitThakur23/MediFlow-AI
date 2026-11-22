from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Encounter, Hospital, HospitalUser, Patient, User


@pytest.fixture
def engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def connection(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        Base.metadata.drop_all(connection)
    engine.dispose()


@pytest.fixture
def db_session(engine):
    with Session(engine) as db:
        yield db


@pytest.fixture
def client(engine):
    def override_get_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


AUTH = ("doctor.synthetic@example.test", "Synthetic-Password-123")


def make_context(db: Session, code: str = "C9-A"):
    hospital = Hospital(name=f"Synthetic {code}", code=code)
    db.add(hospital)
    db.flush()
    user = User(
        email="doctor.synthetic@example.test",
        display_name="Synthetic Doctor",
        status="active",
        password_hash=hash_password("Synthetic-Password-123"),
    )
    db.add(user)
    db.flush()
    doctor = HospitalUser(
        hospital=hospital,
        user=user,
        role_code="doctor",
        relationship_scope="hospital",
        status="active",
        valid_from=datetime(2026, 11, 22, tzinfo=timezone.utc),
    )
    patient = Patient(
        hospital=hospital,
        synthetic_mrn=f"{code}-MRN",
        given_name="Synthetic",
        family_name="Patient",
        date_of_birth=date(2000, 1, 1),
        identity_status="unverified",
    )
    db.add_all([doctor, patient])
    db.flush()
    encounter = Encounter(
        hospital=hospital,
        patient=patient,
        doctor_hospital_user=doctor,
        status="planned",
    )
    db.add(encounter)
    db.commit()
    return hospital, doctor, patient, encounter


def headers(hospital: Hospital) -> dict[str, str]:
    return {
        "X-Hospital-Id": str(hospital.id),
        "X-Mediflow-Purpose": "synthetic document workflow testing",
    }


def create_document(
    client: TestClient,
    hospital: Hospital,
    patient: Patient,
    encounter=None,
) -> dict:
    body = {
        "patient_id": str(patient.id),
        "document_type": "laboratory_report",
        "original_name": "synthetic-report.pdf",
        "mime_type": "application/pdf",
        "object_uri": "synthetic://documents/report-001",
        "sha256": "a" * 64,
        "document_date": "2026-11-20",
        "issuing_source": "Synthetic Laboratory",
        "page_count": 2,
        "processing_status": "uploaded",
        "retention_status": "active",
    }
    if encounter is not None:
        body["encounter_id"] = str(encounter.id)
    response = client.post(
        "/api/v1/documents",
        headers=headers(hospital),
        auth=AUTH,
        json=body,
    )
    assert response.status_code == 201
    return response.json()


def test_document_metadata_create_get_list(client, db_session):
    hospital, _doctor, patient, encounter = make_context(db_session)
    document = create_document(client, hospital, patient, encounter)

    get_document = client.get(
        f"/api/v1/documents/{document['id']}",
        headers=headers(hospital),
        auth=AUTH,
    )
    assert get_document.status_code == 200
    assert get_document.json()["original_name"] == "synthetic-report.pdf"

    listing = client.get(
        "/api/v1/documents",
        headers=headers(hospital),
        auth=AUTH,
    )
    assert listing.status_code == 200
    assert [row["id"] for row in listing.json()] == [document["id"]]


def test_document_rejects_unsupported_mime_and_bad_sha(client, db_session):
    hospital, _doctor, patient, _encounter = make_context(db_session)

    unsupported = client.post(
        "/api/v1/documents",
        headers=headers(hospital),
        auth=AUTH,
        json={
            "patient_id": str(patient.id),
            "document_type": "report",
            "original_name": "report.exe",
            "mime_type": "application/octet-stream",
            "object_uri": "synthetic://documents/report.exe",
        },
    )
    assert unsupported.status_code == 422

    bad_sha = client.post(
        "/api/v1/documents",
        headers=headers(hospital),
        auth=AUTH,
        json={
            "patient_id": str(patient.id),
            "document_type": "report",
            "original_name": "report.pdf",
            "mime_type": "application/pdf",
            "object_uri": "synthetic://documents/report.pdf",
            "sha256": "not-a-64-character-hash",
        },
    )
    assert bad_sha.status_code == 422


def test_document_cross_hospital_and_cross_patient_encounter(client, db_session):
    hospital, _doctor, patient, encounter = make_context(db_session)

    mismatch_encounter = client.post(
        "/api/v1/documents",
        headers=headers(hospital),
        auth=AUTH,
        json={
            "patient_id": str(patient.id),
            "encounter_id": str(encounter.id),
            "document_type": "report",
            "original_name": "report.pdf",
            "mime_type": "application/pdf",
            "object_uri": "synthetic://documents/report.pdf",
        },
    )
    assert mismatch_encounter.status_code == 201

    other_patient = Patient(
        hospital=hospital,
        synthetic_mrn="C9-OTHER",
        given_name="Other",
        family_name="Patient",
        date_of_birth=date(2001, 1, 1),
        identity_status="unverified",
    )
    db_session.add(other_patient)
    db_session.commit()

    mismatch = client.post(
        "/api/v1/documents",
        headers=headers(hospital),
        auth=AUTH,
        json={
            "patient_id": str(other_patient.id),
            "encounter_id": str(encounter.id),
            "document_type": "report",
            "original_name": "report.pdf",
            "mime_type": "application/pdf",
            "object_uri": "synthetic://documents/report.pdf",
        },
    )
    assert mismatch.status_code == 409


def test_page_region_extraction_correction_and_source_navigation(client, db_session):
    hospital, _doctor, patient, encounter = make_context(db_session)
    document = create_document(client, hospital, patient, encounter)

    page = client.post(
        f"/api/v1/documents/{document['id']}/pages",
        headers=headers(hospital),
        auth=AUTH,
        json={
            "page_number": 1,
            "width": 612,
            "height": 792,
            "text_source": "synthetic selectable text",
        },
    )
    assert page.status_code == 201

    region = client.post(
        f"/api/v1/documents/{document['id']}/pages/{page.json()['id']}/regions",
        headers=headers(hospital),
        auth=AUTH,
        json={
            "region_type": "table_cell",
            "x": "10.25",
            "y": "20.50",
            "width": "100.00",
            "height": "15.00",
            "text": "Synthetic result",
            "confidence": "0.8750",
        },
    )
    assert region.status_code == 201
    assert region.json()["text"] == "Synthetic result"

    extraction = client.post(
        f"/api/v1/documents/{document['id']}/extractions",
        headers=headers(hospital),
        auth=AUTH,
        json={
            "document_region_id": region.json()["id"],
            "field_name": "synthetic_test",
            "extracted_value": "12.5",
            "normalized_value": "12.5",
            "unit": "synthetic-unit",
            "reference_range": "10-15",
            "extraction_status": "review_required",
            "confidence": "0.8750",
        },
    )
    assert extraction.status_code == 201

    correction = client.post(
        f"/api/v1/documents/{document['id']}/extractions/{extraction.json()['id']}/corrections",
        headers=headers(hospital),
        auth=AUTH,
        json={
            "previous_value": "12.5",
            "corrected_value": "13.0",
            "reason": "Synthetic human verification",
        },
    )
    assert correction.status_code == 201
    assert correction.json()["corrected_value"] == "13.0"

    pages = client.get(
        f"/api/v1/documents/{document['id']}/pages",
        headers=headers(hospital),
        auth=AUTH,
    )
    assert pages.status_code == 200
    assert pages.json()[0]["page_number"] == 1

    extractions = client.get(
        f"/api/v1/documents/{document['id']}/extractions",
        headers=headers(hospital),
        auth=AUTH,
    )
    assert extractions.status_code == 200
    assert extractions.json()[0]["document_region_id"] == region.json()["id"]


def test_extraction_rejects_region_from_another_document(client, db_session):
    hospital, _doctor, patient, encounter = make_context(db_session)
    first_document = create_document(client, hospital, patient, encounter)
    second_document = create_document(client, hospital, patient, encounter)

    page = client.post(
        f"/api/v1/documents/{first_document['id']}/pages",
        headers=headers(hospital),
        auth=AUTH,
        json={"page_number": 1},
    )
    region = client.post(
        f"/api/v1/documents/{first_document['id']}/pages/{page.json()['id']}/regions",
        headers=headers(hospital),
        auth=AUTH,
        json={"region_type": "text", "text": "Synthetic text"},
    )

    mismatch = client.post(
        f"/api/v1/documents/{second_document['id']}/extractions",
        headers=headers(hospital),
        auth=AUTH,
        json={
            "document_region_id": region.json()["id"],
            "field_name": "wrong_document_field",
            "extraction_status": "review_required",
        },
    )
    assert mismatch.status_code == 409


def test_cross_hospital_document_is_not_visible(client, db_session):
    first_hospital, _doctor, patient, encounter = make_context(db_session)
    first_document = create_document(client, first_hospital, patient, encounter)

    second_hospital = Hospital(name="Synthetic C9-B", code="C9-B")
    db_session.add(second_hospital)
    db_session.flush()
    second_document = Patient(
        hospital=second_hospital,
        synthetic_mrn="C9-B-MRN",
        given_name="Cross",
        family_name="Tenant",
        date_of_birth=date(2000, 1, 1),
        identity_status="unverified",
    )
    db_session.add(second_document)
    db_session.commit()

    response = client.get(
        f"/api/v1/documents/{first_document['id']}",
        headers={
            "X-Hospital-Id": str(second_hospital.id),
            "X-Mediflow-Purpose": "synthetic document isolation test",
        },
        auth=AUTH,
    )
    assert response.status_code in {403, 404}
