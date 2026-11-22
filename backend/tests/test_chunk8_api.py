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
from app.models import (
    AllergyIntolerance,
    Encounter,
    Hospital,
    HospitalUser,
    MedicationStatement,
    Patient,
    ProvenanceRecord,
    User,
)


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


def make_assignment(
    db: Session,
    hospital: Hospital,
    email: str,
    role_code: str,
) -> tuple[User, HospitalUser]:
    user = User(
        email=email,
        display_name=f"Synthetic {role_code}",
        status="active",
        password_hash=hash_password("Synthetic-Password-123"),
    )
    db.add(user)
    db.flush()
    assignment = HospitalUser(
        hospital=hospital,
        user=user,
        role_code=role_code,
        relationship_scope="hospital",
        status="active",
        valid_from=datetime(2026, 11, 22, tzinfo=timezone.utc),
    )
    db.add(assignment)
    db.commit()
    return user, assignment


def make_context(db: Session, code: str = "C8-A"):
    hospital = Hospital(name=f"Synthetic {code}", code=code)
    db.add(hospital)
    db.flush()
    _doctor_user, doctor = make_assignment(
        db,
        hospital,
        "doctor.synthetic@example.test",
        "doctor",
    )
    _pharmacist_user, pharmacist = make_assignment(
        db,
        hospital,
        "pharmacist.synthetic@example.test",
        "pharmacist",
    )
    patient = Patient(
        hospital=hospital,
        synthetic_mrn=f"{code}-MRN",
        given_name="Synthetic",
        family_name="Patient",
        date_of_birth=date(2000, 1, 1),
        identity_status="unverified",
    )
    encounter = Encounter(
        hospital=hospital,
        patient=patient,
        doctor_hospital_user=doctor,
        status="planned",
    )
    db.add_all([patient, encounter])
    db.commit()
    return hospital, doctor, pharmacist, patient, encounter


def auth_for(email: str = "doctor.synthetic@example.test"):
    return (email, "Synthetic-Password-123")


def headers(hospital: Hospital) -> dict[str, str]:
    return {
        "X-Hospital-Id": str(hospital.id),
        "X-Mediflow-Purpose": "synthetic prescription workflow testing",
    }


def create_catalogue_item(client: TestClient, hospital: Hospital) -> dict:
    response = client.post(
        "/api/v1/catalogue/items",
        headers=headers(hospital),
        auth=auth_for(),
        json={
            "catalogue_name": "Synthetic Academic Catalogue",
            "catalogue_version": "2026.11",
            "generic_name": "synthetic medicine",
            "brand_name": "Synthetic Brand",
            "active_ingredient": "synthetic ingredient",
            "manufacturer": "Synthetic manufacturer",
            "strength": "10 mg",
            "dosage_form": "tablet",
            "route": "oral",
            "prescribing_information": "Synthetic educational record only",
            "source_name": "Synthetic source",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_catalogue_creation_and_search(client, db_session):
    hospital, _doctor, _pharmacist, _patient, _encounter = make_context(db_session)
    item = create_catalogue_item(client, hospital)

    search = client.get(
        "/api/v1/catalogue/items",
        headers=headers(hospital),
        auth=auth_for("pharmacist.synthetic@example.test"),
        params={"q": "synthetic medicine"},
    )

    assert search.status_code == 200
    assert [row["id"] for row in search.json()] == [item["id"]]


def test_prescription_draft_approval_signing_and_pharmacy_view(client, db_session):
    hospital, doctor, pharmacist, patient, encounter = make_context(db_session)
    item = create_catalogue_item(client, hospital)

    draft_response = client.post(
        "/api/v1/prescription-drafts",
        headers=headers(hospital),
        auth=auth_for(),
        json={
            "patient_id": str(patient.id),
            "encounter_id": str(encounter.id),
            "lines": [
                {
                    "catalogue_item_id": item["id"],
                    "medicine_name": "synthetic medicine",
                    "strength": "10 mg",
                    "dose": "one tablet",
                    "route": "oral",
                    "frequency": "once daily",
                    "duration": "3 days",
                    "quantity": "3",
                    "instructions": "Synthetic educational instructions",
                }
            ],
        },
    )
    assert draft_response.status_code == 201
    draft = draft_response.json()

    get_draft = client.get(
        f"/api/v1/prescription-drafts/{draft['id']}",
        headers=headers(hospital),
        auth=auth_for(),
    )
    assert get_draft.status_code == 200
    assert get_draft.json()["status"] == "draft"

    approval = client.patch(
        f"/api/v1/prescription-drafts/{draft['id']}/approval",
        headers=headers(hospital),
        auth=auth_for(),
        json={"approved": True},
    )
    assert approval.status_code == 200
    assert approval.json()["status"] == "approved"

    signing = client.post(
        "/api/v1/prescriptions",
        headers=headers(hospital),
        auth=auth_for(),
        params={"draft_id": draft["id"]},
        json={"signature_reference": "synthetic-signature-001"},
    )
    assert signing.status_code == 201
    prescription = signing.json()
    assert prescription["prescribing_hospital_user_id"] == str(doctor.id)
    assert prescription["status"] == "signed"
    assert len(prescription["lines"]) == 1

    pharmacy_view = client.get(
        f"/api/v1/pharmacy/prescriptions/{prescription['id']}",
        headers=headers(hospital),
        auth=auth_for("pharmacist.synthetic@example.test"),
    )
    assert pharmacy_view.status_code == 200
    assert pharmacy_view.json()["patient_id"] == str(patient.id)
    assert len(pharmacy_view.json()["lines"]) == 1

    dispensing = client.post(
        "/api/v1/dispensing",
        headers=headers(hospital),
        auth=auth_for("pharmacist.synthetic@example.test"),
        json={"prescription_id": prescription["id"]},
    )
    assert dispensing.status_code == 201
    assert dispensing.json()["pharmacist_hospital_user_id"] == str(pharmacist.id)
    assert dispensing.json()["status"] == "viewed"


def test_unsigned_draft_cannot_be_signed(client, db_session):
    hospital, _doctor, _pharmacist, patient, encounter = make_context(db_session)

    draft_response = client.post(
        "/api/v1/prescription-drafts",
        headers=headers(hospital),
        auth=auth_for(),
        json={
            "patient_id": str(patient.id),
            "encounter_id": str(encounter.id),
            "lines": [{"medicine_name": "unknown synthetic medicine"}],
        },
    )
    assert draft_response.status_code == 201

    signing = client.post(
        "/api/v1/prescriptions",
        headers=headers(hospital),
        auth=auth_for(),
        params={"draft_id": draft_response.json()["id"]},
        json={"signature_reference": "must-not-sign"},
    )
    assert signing.status_code == 409


def test_non_doctor_cannot_create_or_sign(client, db_session):
    hospital, _doctor, _pharmacist, patient, encounter = make_context(db_session)

    draft = client.post(
        "/api/v1/prescription-drafts",
        headers=headers(hospital),
        auth=auth_for("pharmacist.synthetic@example.test"),
        json={
            "patient_id": str(patient.id),
            "encounter_id": str(encounter.id),
            "lines": [{"medicine_name": "forbidden by role"}],
        },
    )
    assert draft.status_code == 403


def test_draft_rejects_cross_hospital_encounter(client, db_session):
    hospital, _doctor, _pharmacist, patient, _encounter = make_context(db_session)
    other_hospital = Hospital(name="Synthetic C8-B", code="C8-B")
    db_session.add(other_hospital)
    db_session.flush()
    other_patient = Patient(
        hospital=other_hospital,
        synthetic_mrn="C8-B-MRN",
        given_name="Cross",
        family_name="Patient",
        date_of_birth=date(2000, 1, 1),
        identity_status="unverified",
    )
    db_session.add(other_patient)
    other_user = User(
        email="other.synthetic@example.test",
        display_name="Other synthetic doctor",
        status="active",
        password_hash=hash_password("Synthetic-Password-123"),
    )
    db_session.add(other_user)
    db_session.flush()
    other_doctor = HospitalUser(
        hospital=other_hospital,
        user=other_user,
        role_code="doctor",
        relationship_scope="hospital",
        status="active",
        valid_from=datetime(2026, 11, 22, tzinfo=timezone.utc),
    )
    db_session.add_all([other_doctor])
    db_session.flush()
    other_encounter = Encounter(
        hospital=other_hospital,
        patient=other_patient,
        doctor_hospital_user=other_doctor,
        status="planned",
    )
    db_session.add_all([other_patient, other_encounter])
    db_session.commit()

    response = client.post(
        "/api/v1/prescription-drafts",
        headers=headers(hospital),
        auth=auth_for(),
        json={
            "patient_id": str(patient.id),
            "encounter_id": str(other_encounter.id),
            "lines": [{"medicine_name": "synthetic medicine"}],
        },
    )
    assert response.status_code == 404


def test_exact_allergy_and_duplicate_therapy_warnings(client, db_session):
    hospital, _doctor, _pharmacist, patient, encounter = make_context(db_session)
    provenance = ProvenanceRecord(
        hospital=hospital,
        patient=patient,
        source_type="doctor_entry",
        recorded_at=datetime.now(timezone.utc),
        verification_status="reviewed",
        uncertainty="unknown",
    )
    db_session.add(provenance)
    db_session.flush()
    allergy = AllergyIntolerance(
        hospital=hospital,
        patient=patient,
        provenance=provenance,
        substance="synthetic medicine",
        criticality="high",
        status="active",
        verification_status="verified",
    )
    medication = MedicationStatement(
        hospital=hospital,
        patient=patient,
        provenance=provenance,
        medicine_name="synthetic medicine",
        statement_type="prescribed",
        status="active",
        verification_status="verified",
    )
    db_session.add_all([allergy, medication])
    db_session.commit()

    draft = client.post(
        "/api/v1/prescription-drafts",
        headers=headers(hospital),
        auth=auth_for(),
        json={
            "patient_id": str(patient.id),
            "encounter_id": str(encounter.id),
            "lines": [{"medicine_name": "synthetic medicine"}],
        },
    )

    assert draft.status_code == 201
    warnings = draft.json()["safety_warnings"]
    assert any("allergy" in warning.lower() for warning in warnings)
    assert any("duplicate" in warning.lower() for warning in warnings)


def test_pharmacy_cannot_create_doctor_draft(client, db_session):
    hospital, _doctor, _pharmacist, patient, encounter = make_context(db_session)

    response = client.post(
        "/api/v1/prescription-drafts",
        headers=headers(hospital),
        auth=auth_for("pharmacist.synthetic@example.test"),
        json={
            "patient_id": str(patient.id),
            "encounter_id": str(encounter.id),
            "lines": [{"medicine_name": "not permitted"}],
        },
    )
    assert response.status_code == 403
