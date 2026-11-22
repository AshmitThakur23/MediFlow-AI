from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session

from app.core.config import settings
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
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
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


def make_context(db: Session):
    hospital = Hospital(name="Synthetic AI Hospital", code="AI-SYN")
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
        synthetic_mrn="AI-SYN-MRN",
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
    return hospital, patient, encounter


def headers(hospital: Hospital):
    return {
        "X-Hospital-Id": str(hospital.id),
        "X-Mediflow-Purpose": "synthetic Gemini draft verification",
    }


def test_ai_draft_returns_service_unavailable_when_key_is_missing(
    client,
    db_session,
    monkeypatch,
):
    hospital, patient, encounter = make_context(db_session)
    monkeypatch.setattr(settings, "gemini_api_key", None)

    response = client.post(
        "/api/v1/ai/clinical-draft",
        headers=headers(hospital),
        auth=AUTH,
        json={
            "patient_id": str(patient.id),
            "encounter_id": str(encounter.id),
            "transcript": "Synthetic patient reports a dry cough for three days. No fever.",
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "GEMINI_API_KEY is not configured"


def test_clinical_note_template_save_and_approval(client, db_session):
    hospital, patient, encounter = make_context(db_session)

    saved = client.post(
        "/api/v1/clinical-notes/drafts",
        headers=headers(hospital),
        auth=AUTH,
        json={
            "patient_id": str(patient.id),
            "encounter_id": str(encounter.id),
            "transcript_text": "Patient reports a dry cough for three days.",
            "chief_complaint": "Dry cough",
            "history": "Three-day cough.",
            "patient_facts": "Dry cough without fever.",
            "doctor_questions": "Associated symptoms?",
            "examination_findings": "Pending examination.",
            "assessment": "Draft only.",
            "plan": "Follow-up in two weeks.",
            "missing_information": "Physical examination findings.",
        },
    )
    assert saved.status_code == 201
    assert saved.json()["status"] == "draft"

    approved = client.patch(
        f"/api/v1/clinical-notes/drafts/{saved.json()['id']}/approval",
        headers=headers(hospital),
        auth=AUTH,
        json={"approved": True},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    listing = client.get(
        "/api/v1/clinical-notes/drafts",
        headers=headers(hospital),
        auth=AUTH,
        params={"patient_id": str(patient.id)},
    )
    assert listing.status_code == 200
    assert listing.json()[0]["chief_complaint"] == "Dry cough"
