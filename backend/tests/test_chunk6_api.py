from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Hospital, HospitalUser, Patient, User


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
    Base.metadata.drop_all(engine)
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


AUTH = (
    "doctor.synthetic@example.test",
    "Synthetic-Password-123",
)


def make_account(
    db: Session,
    *,
    hospital_code: str = "C6-A",
    role_code: str = "doctor",
    relationship_scope: str = "hospital",
) -> tuple[Hospital, HospitalUser]:
    hospital = Hospital(name=f"Synthetic {hospital_code}", code=hospital_code)
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
    assignment = HospitalUser(
        hospital=hospital,
        user=user,
        role_code=role_code,
        relationship_scope=relationship_scope,
        status="active",
        valid_from=datetime(2026, 11, 22, tzinfo=timezone.utc),
    )
    db.add(assignment)
    db.commit()
    return hospital, assignment


def request_headers(hospital: Hospital) -> dict[str, str]:
    return {
        "X-Hospital-Id": str(hospital.id),
        "X-Mediflow-Purpose": "synthetic clinical workflow testing",
    }


def create_patient(
    client: TestClient,
    hospital: Hospital,
    mrn: str = "C6-MRN-001",
) -> dict:
    response = client.post(
        "/api/v1/patients",
        headers=request_headers(hospital),
        auth=AUTH,
        json={
            "synthetic_mrn": mrn,
            "given_name": "Synthetic",
            "family_name": "Patient",
            "date_of_birth": "2000-01-01",
            "sex_at_birth": "unknown",
            "identity_status": "unverified",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_patient_profile_create_search_get_and_timeline(client, db_session):
    hospital, _assignment = make_account(db_session)
    patient = create_patient(client, hospital)

    search = client.get(
        "/api/v1/patients",
        headers=request_headers(hospital),
        auth=AUTH,
        params={"q": "C6-MRN"},
    )
    assert search.status_code == 200
    assert [row["id"] for row in search.json()] == [patient["id"]]

    get = client.get(
        f"/api/v1/patients/{patient['id']}",
        headers=request_headers(hospital),
        auth=AUTH,
    )
    assert get.status_code == 200
    assert get.json()["synthetic_mrn"] == "C6-MRN-001"

    timeline = client.get(
        f"/api/v1/patients/{patient['id']}/timeline",
        headers=request_headers(hospital),
        auth=AUTH,
    )
    assert timeline.status_code == 200
    assert timeline.json() == []


def test_patient_create_rejects_duplicate_mrn(client, db_session):
    hospital, _assignment = make_account(db_session)
    create_patient(client, hospital)

    duplicate = client.post(
        "/api/v1/patients",
        headers=request_headers(hospital),
        auth=AUTH,
        json={
            "synthetic_mrn": "C6-MRN-001",
            "given_name": "Duplicate",
            "family_name": "Patient",
            "date_of_birth": "2001-01-01",
            "identity_status": "unverified",
        },
    )

    assert duplicate.status_code == 409


def test_patient_rejects_cross_hospital_id(client, db_session):
    first_hospital, _assignment = make_account(
        db_session,
        hospital_code="C6-CROSS-A",
    )
    second_hospital = Hospital(
        name="Synthetic C6-CROSS-B",
        code="C6-CROSS-B",
    )
    db_session.add(second_hospital)
    db_session.flush()
    patient = Patient(
        hospital=second_hospital,
        synthetic_mrn="C6-CROSS-MRN",
        given_name="Synthetic",
        family_name="CrossTenant",
        date_of_birth=date(2000, 1, 1),
        identity_status="unverified",
    )
    db_session.add(patient)
    db_session.commit()

    response = client.get(
        f"/api/v1/patients/{patient.id}",
        headers=request_headers(first_hospital),
        auth=AUTH,
    )

    assert response.status_code == 404


def test_appointment_create_list_get_and_status_update(client, db_session):
    hospital, doctor = make_account(db_session)
    patient = create_patient(client, hospital)
    scheduled_at = "2026-11-22T10:00:00Z"

    create = client.post(
        "/api/v1/appointments",
        headers=request_headers(hospital),
        auth=AUTH,
        json={
            "patient_id": patient["id"],
            "doctor_hospital_user_id": str(doctor.id),
            "scheduled_at": scheduled_at,
        },
    )
    assert create.status_code == 201
    appointment = create.json()
    assert appointment["status"] == "scheduled"

    get = client.get(
        f"/api/v1/appointments/{appointment['id']}",
        headers=request_headers(hospital),
        auth=AUTH,
    )
    assert get.status_code == 200

    listing = client.get(
        "/api/v1/appointments",
        headers=request_headers(hospital),
        auth=AUTH,
        params={"patient_id": patient["id"]},
    )
    assert listing.status_code == 200
    assert [row["id"] for row in listing.json()] == [appointment["id"]]

    update = client.patch(
        f"/api/v1/appointments/{appointment['id']}/status",
        headers=request_headers(hospital),
        auth=AUTH,
        json={"status": "checked_in"},
    )
    assert update.status_code == 200
    assert update.json()["status"] == "checked_in"


def test_appointment_rejects_unknown_or_cross_hospital_patient(
    client,
    db_session,
):
    hospital, doctor = make_account(
        db_session,
        hospital_code="C6-APPT-A",
    )
    second_hospital = Hospital(
        name="Synthetic C6-APPT-B",
        code="C6-APPT-B",
    )
    db_session.add(second_hospital)
    db_session.flush()
    cross_patient = Patient(
        hospital=second_hospital,
        synthetic_mrn="C6-APPT-CROSS",
        given_name="Cross",
        family_name="Patient",
        date_of_birth=date(2000, 1, 1),
        identity_status="unverified",
    )
    db_session.add(cross_patient)
    db_session.commit()

    response = client.post(
        "/api/v1/appointments",
        headers=request_headers(hospital),
        auth=AUTH,
        json={
            "patient_id": str(cross_patient.id),
            "doctor_hospital_user_id": str(doctor.id),
            "scheduled_at": "2026-11-22T10:00:00Z",
        },
    )

    assert response.status_code == 404


def test_appointment_rejects_invalid_status(client, db_session):
    hospital, doctor = make_account(
        db_session,
        hospital_code="C6-STATUS",
    )
    patient = create_patient(client, hospital, "C6-STATUS-MRN")
    create = client.post(
        "/api/v1/appointments",
        headers=request_headers(hospital),
        auth=AUTH,
        json={
            "patient_id": patient["id"],
            "doctor_hospital_user_id": str(doctor.id),
            "scheduled_at": "2026-11-22T10:00:00Z",
        },
    )
    appointment_id = create.json()["id"]

    update = client.patch(
        f"/api/v1/appointments/{appointment_id}/status",
        headers=request_headers(hospital),
        auth=AUTH,
        json={"status": "fake_status"},
    )

    assert update.status_code == 422


def test_encounter_create_get_update_and_timeline(client, db_session):
    hospital, doctor = make_account(db_session)
    patient = create_patient(client, hospital, "C6-ENCOUNTER-MRN")
    appointment = client.post(
        "/api/v1/appointments",
        headers=request_headers(hospital),
        auth=AUTH,
        json={
            "patient_id": patient["id"],
            "doctor_hospital_user_id": str(doctor.id),
            "scheduled_at": "2026-11-22T10:00:00Z",
        },
    ).json()

    create = client.post(
        "/api/v1/encounters",
        headers=request_headers(hospital),
        auth=AUTH,
        json={
            "patient_id": patient["id"],
            "appointment_id": appointment["id"],
            "doctor_hospital_user_id": str(doctor.id),
            "started_at": "2026-11-22T10:05:00Z",
            "status": "in_progress",
        },
    )
    assert create.status_code == 201
    encounter = create.json()

    get = client.get(
        f"/api/v1/encounters/{encounter['id']}",
        headers=request_headers(hospital),
        auth=AUTH,
    )
    assert get.status_code == 200

    update = client.patch(
        f"/api/v1/encounters/{encounter['id']}/status",
        headers=request_headers(hospital),
        auth=AUTH,
        json={
            "status": "completed",
            "ended_at": "2026-11-22T10:30:00Z",
        },
    )
    assert update.status_code == 200
    assert update.json()["status"] == "completed"

    timeline = client.get(
        f"/api/v1/patients/{patient['id']}/timeline",
        headers=request_headers(hospital),
        auth=AUTH,
    )
    assert timeline.status_code == 200
    item_types = {item["item_type"] for item in timeline.json()}
    assert item_types == {"appointment", "encounter"}


def test_encounter_rejects_mismatched_appointment_patient(client, db_session):
    hospital, doctor = make_account(db_session)
    first_patient = create_patient(client, hospital, "C6-MISMATCH-A")
    second_patient = create_patient(client, hospital, "C6-MISMATCH-B")
    appointment = client.post(
        "/api/v1/appointments",
        headers=request_headers(hospital),
        auth=AUTH,
        json={
            "patient_id": first_patient["id"],
            "doctor_hospital_user_id": str(doctor.id),
            "scheduled_at": "2026-11-22T10:00:00Z",
        },
    ).json()

    mismatch = client.post(
        "/api/v1/encounters",
        headers=request_headers(hospital),
        auth=AUTH,
        json={
            "patient_id": second_patient["id"],
            "appointment_id": appointment["id"],
            "doctor_hospital_user_id": str(doctor.id),
            "status": "planned",
        },
    )

    assert mismatch.status_code == 409


def test_encounter_rejects_invalid_time_and_status(client, db_session):
    hospital, doctor = make_account(db_session)
    patient = create_patient(client, hospital, "C6-TIME-MRN")

    invalid_time = client.post(
        "/api/v1/encounters",
        headers=request_headers(hospital),
        auth=AUTH,
        json={
            "patient_id": patient["id"],
            "doctor_hospital_user_id": str(doctor.id),
            "started_at": "2026-11-22T11:00:00Z",
            "ended_at": "2026-11-22T10:00:00Z",
            "status": "planned",
        },
    )
    assert invalid_time.status_code == 422

    invalid_status = client.post(
        "/api/v1/encounters",
        headers=request_headers(hospital),
        auth=AUTH,
        json={
            "patient_id": patient["id"],
            "doctor_hospital_user_id": str(doctor.id),
            "status": "fake_status",
        },
    )
    assert invalid_status.status_code == 422


def test_restricted_patient_relationship_scope_fails_closed(
    client,
    db_session,
):
    hospital, _assignment = make_account(
        db_session,
        hospital_code="C6-SCOPE",
        relationship_scope="patient_relationship",
    )
    patient = create_patient(client, hospital, "C6-SCOPE-MRN")

    get_patient = client.get(
        f"/api/v1/patients/{patient['id']}",
        headers=request_headers(hospital),
        auth=AUTH,
    )
    assert get_patient.status_code == 403

    search = client.get(
        "/api/v1/patients",
        headers=request_headers(hospital),
        auth=AUTH,
    )
    assert search.status_code == 403
