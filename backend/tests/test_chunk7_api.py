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
from app.models import (
    Encounter,
    Hospital,
    HospitalUser,
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


AUTH = ("doctor.synthetic@example.test", "Synthetic-Password-123")


def make_context(db: Session, code: str = "C7-A"):
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
    db.commit()
    return hospital, doctor, patient


def headers(hospital: Hospital) -> dict[str, str]:
    return {
        "X-Hospital-Id": str(hospital.id),
        "X-Mediflow-Purpose": "synthetic clinical history testing",
    }


def create_provenance(
    client: TestClient,
    hospital: Hospital,
    patient: Patient | None = None,
    encounter_id=None,
    author_id=None,
) -> dict:
    body = {
        "source_type": "doctor_entry",
        "recorded_at": "2026-11-22T10:00:00Z",
        "verification_status": "reviewed",
        "uncertainty": "unknown",
        "confidence": "0.8750",
    }
    if patient is not None:
        body["patient_id"] = str(patient.id)
    if encounter_id is not None:
        body["encounter_id"] = str(encounter_id)
    if author_id is not None:
        body["author_hospital_user_id"] = str(author_id)
    response = client.post(
        "/api/v1/provenance",
        headers=headers(hospital),
        auth=AUTH,
        json=body,
    )
    assert response.status_code == 201
    return response.json()


def test_hospital_and_patient_provenance_creation_and_listing(client, db_session):
    hospital, doctor, patient = make_context(db_session)

    hospital_level = create_provenance(client, hospital)
    assert hospital_level["patient_id"] is None
    assert hospital_level["encounter_id"] is None

    patient_level = create_provenance(client, hospital, patient, author_id=doctor.id)
    assert patient_level["patient_id"] == str(patient.id)
    assert patient_level["author_hospital_user_id"] == str(doctor.id)

    listing = client.get(
        "/api/v1/provenance",
        headers=headers(hospital),
        auth=AUTH,
        params={"patient_id": str(patient.id)},
    )
    assert listing.status_code == 200
    assert [row["id"] for row in listing.json()] == [patient_level["id"]]


def test_encounter_linked_provenance_requires_same_patient(client, db_session):
    hospital, doctor, patient = make_context(db_session)
    encounter = Encounter(
        hospital=hospital,
        patient=patient,
        doctor_hospital_user=doctor,
        status="planned",
    )
    other_patient = Patient(
        hospital=hospital,
        synthetic_mrn="C7-OTHER",
        given_name="Other",
        family_name="Patient",
        date_of_birth=date(2001, 1, 1),
        identity_status="unverified",
    )
    db_session.add_all([encounter, other_patient])
    db_session.commit()

    valid = create_provenance(
        client,
        hospital,
        patient,
        encounter_id=encounter.id,
    )
    assert valid["encounter_id"] == str(encounter.id)

    mismatch = client.post(
        "/api/v1/provenance",
        headers=headers(hospital),
        auth=AUTH,
        json={
            "patient_id": str(other_patient.id),
            "encounter_id": str(encounter.id),
            "source_type": "conversation",
            "recorded_at": "2026-11-22T10:10:00Z",
            "verification_status": "unverified",
            "uncertainty": "unknown",
        },
    )
    assert mismatch.status_code == 409


def test_encounter_linked_provenance_rejects_missing_patient(client, db_session):
    hospital, doctor, patient = make_context(db_session)
    encounter = Encounter(
        hospital=hospital,
        patient=patient,
        doctor_hospital_user=doctor,
        status="planned",
    )
    db_session.add(encounter)
    db_session.commit()

    response = client.post(
        "/api/v1/provenance",
        headers=headers(hospital),
        auth=AUTH,
        json={
            "encounter_id": str(encounter.id),
            "source_type": "conversation",
            "recorded_at": "2026-11-22T10:10:00Z",
            "verification_status": "unverified",
            "uncertainty": "unknown",
        },
    )
    assert response.status_code == 409


def test_cross_hospital_and_invalid_provenance_controls(client, db_session):
    hospital, _doctor, patient = make_context(db_session)
    other_hospital = Hospital(name="Synthetic C7-B", code="C7-B")
    db_session.add(other_hospital)
    db_session.flush()
    other_patient = Patient(
        hospital=other_hospital,
        synthetic_mrn="C7-B-MRN",
        given_name="Cross",
        family_name="Patient",
        date_of_birth=date(2000, 1, 1),
        identity_status="unverified",
    )
    db_session.add(other_patient)
    db_session.commit()

    cross_patient = client.post(
        "/api/v1/provenance",
        headers=headers(hospital),
        auth=AUTH,
        json={
            "patient_id": str(other_patient.id),
            "source_type": "import",
            "recorded_at": "2026-11-22T10:10:00Z",
            "verification_status": "unverified",
            "uncertainty": "unknown",
        },
    )
    assert cross_patient.status_code == 404

    invalid_source = client.post(
        "/api/v1/provenance",
        headers=headers(hospital),
        auth=AUTH,
        json={
            "patient_id": str(patient.id),
            "source_type": "unsupported",
            "recorded_at": "2026-11-22T10:10:00Z",
            "verification_status": "unverified",
            "uncertainty": "unknown",
        },
    )
    assert invalid_source.status_code == 422

    invalid_verification = client.post(
        "/api/v1/provenance",
        headers=headers(hospital),
        auth=AUTH,
        json={
            "patient_id": str(patient.id),
            "source_type": "import",
            "recorded_at": "2026-11-22T10:10:00Z",
            "verification_status": "unsupported",
            "uncertainty": "unknown",
        },
    )
    assert invalid_verification.status_code == 422


def test_condition_allergy_observation_and_medication_creation(client, db_session):
    hospital, _doctor, patient = make_context(db_session)
    provenance = create_provenance(client, hospital, patient)
    catalogue = client.post(
        "/api/v1/catalogue/items",
        headers=headers(hospital),
        auth=AUTH,
        json={
            "catalogue_name": "Synthetic Academic Catalogue",
            "catalogue_version": "2026.11",
            "generic_name": "Synthetic medicine",
            "source_name": "Synthetic source",
        },
    )
    assert catalogue.status_code == 201

    condition = client.post(
        "/api/v1/conditions",
        headers=headers(hospital),
        auth=AUTH,
        json={
            "patient_id": str(patient.id),
            "provenance_id": provenance["id"],
            "display_name": "Synthetic condition",
            "status": "active",
            "verification_status": "verified",
        },
    )
    assert condition.status_code == 201

    allergy = client.post(
        "/api/v1/allergies",
        headers=headers(hospital),
        auth=AUTH,
        json={
            "patient_id": str(patient.id),
            "provenance_id": provenance["id"],
            "substance": "Synthetic substance",
            "criticality": "unknown",
            "status": "active",
            "verification_status": "unverified",
        },
    )
    assert allergy.status_code == 201

    observation = client.post(
        "/api/v1/observations",
        headers=headers(hospital),
        auth=AUTH,
        json={
            "patient_id": str(patient.id),
            "provenance_id": provenance["id"],
            "observation_type": "laboratory",
            "test_name": "Synthetic test",
            "value_text": "normal",
            "unit": "synthetic-unit",
        },
    )
    assert observation.status_code == 201

    medication = client.post(
        "/api/v1/medications",
        headers=headers(hospital),
        auth=AUTH,
        json={
            "patient_id": str(patient.id),
            "provenance_id": provenance["id"],
            "medicine_name": "Synthetic medicine",
            "catalogue_item_id": catalogue.json()["id"],
            "statement_type": "prescribed",
            "status": "active",
            "verification_status": "reviewed",
        },
    )
    assert medication.status_code == 201
    assert medication.json()["catalogue_item_id"] is not None

    timeline = client.get(
        f"/api/v1/patients/{patient.id}/timeline",
        headers=headers(hospital),
        auth=AUTH,
    )
    assert timeline.status_code == 200
    item_types = {item["item_type"] for item in timeline.json()}
    assert {"condition", "allergy", "observation", "medication"} <= item_types


def test_typed_fact_rejects_cross_hospital_encounter_and_provenance(
    client,
    db_session,
):
    hospital, doctor, patient = make_context(db_session)
    provenance = create_provenance(client, hospital, patient)
    other_hospital = Hospital(name="Synthetic C7-C", code="C7-C")
    db_session.add(other_hospital)
    db_session.flush()
    other_patient = Patient(
        hospital=other_hospital,
        synthetic_mrn="C7-C-MRN",
        given_name="Cross",
        family_name="Encounter",
        date_of_birth=date(2000, 1, 1),
        identity_status="unverified",
    )
    other_doctor = HospitalUser(
        hospital=other_hospital,
        user=User(
            display_name="Other synthetic doctor",
            status="active",
        ),
        role_code="doctor",
        relationship_scope="hospital",
        status="active",
        valid_from=datetime(2026, 11, 22, tzinfo=timezone.utc),
    )
    db_session.add_all([other_patient, other_doctor])
    db_session.flush()
    other_encounter = Encounter(
        hospital=other_hospital,
        patient=other_patient,
        doctor_hospital_user=other_doctor,
        status="planned",
    )
    db_session.add(other_encounter)
    db_session.commit()

    cross_encounter = client.post(
        "/api/v1/conditions",
        headers=headers(hospital),
        auth=AUTH,
        json={
            "patient_id": str(patient.id),
            "encounter_id": str(other_encounter.id),
            "provenance_id": provenance["id"],
            "display_name": "Cross encounter condition",
            "status": "active",
            "verification_status": "verified",
        },
    )
    assert cross_encounter.status_code == 404


def test_typed_fact_rejects_provenance_patient_mismatch(client, db_session):
    hospital, _doctor, patient = make_context(db_session)
    other_patient = Patient(
        hospital=hospital,
        synthetic_mrn="C7-MISMATCH",
        given_name="Mismatch",
        family_name="Patient",
        date_of_birth=date(2000, 1, 1),
        identity_status="unverified",
    )
    db_session.add(other_patient)
    db_session.commit()
    provenance = create_provenance(client, hospital, patient)

    mismatch = client.post(
        "/api/v1/observations",
        headers=headers(hospital),
        auth=AUTH,
        json={
            "patient_id": str(other_patient.id),
            "provenance_id": provenance["id"],
            "observation_type": "laboratory",
            "value_text": "normal",
        },
    )
    assert mismatch.status_code == 409


def test_observation_allergy_and_medication_control_values(client, db_session):
    hospital, _doctor, patient = make_context(db_session)
    provenance = create_provenance(client, hospital, patient)

    observation = client.post(
        "/api/v1/observations",
        headers=headers(hospital),
        auth=AUTH,
        json={
            "patient_id": str(patient.id),
            "provenance_id": provenance["id"],
            "observation_type": "laboratory",
        },
    )
    assert observation.status_code == 422

    allergy = client.post(
        "/api/v1/allergies",
        headers=headers(hospital),
        auth=AUTH,
        json={
            "patient_id": str(patient.id),
            "provenance_id": provenance["id"],
            "substance": "Synthetic",
            "criticality": "critical",
            "status": "active",
            "verification_status": "unverified",
        },
    )
    assert allergy.status_code == 422

    medication = client.post(
        "/api/v1/medications",
        headers=headers(hospital),
        auth=AUTH,
        json={
            "patient_id": str(patient.id),
            "provenance_id": provenance["id"],
            "medicine_name": "Synthetic",
            "statement_type": "prescribed",
            "status": "active",
            "verification_status": "reviewed",
            "start_at": "2026-11-22T11:00:00Z",
            "end_at": "2026-11-22T10:00:00Z",
        },
    )
    assert medication.status_code == 422


def test_same_patient_supersession_and_cross_patient_rejection(client, db_session):
    hospital, _doctor, patient = make_context(db_session)
    provenance = create_provenance(client, hospital, patient)
    first_condition = client.post(
        "/api/v1/conditions",
        headers=headers(hospital),
        auth=AUTH,
        json={
            "patient_id": str(patient.id),
            "provenance_id": provenance["id"],
            "display_name": "First condition",
            "status": "active",
            "verification_status": "verified",
        },
    ).json()

    supersession = client.post(
        "/api/v1/conditions",
        headers=headers(hospital),
        auth=AUTH,
        json={
            "patient_id": str(patient.id),
            "provenance_id": provenance["id"],
            "display_name": "Superseding condition",
            "status": "active",
            "verification_status": "verified",
            "superseded_by_condition_id": first_condition["id"],
        },
    )
    assert supersession.status_code == 201

    other_patient = Patient(
        hospital=hospital,
        synthetic_mrn="C7-SUPER-CROSS",
        given_name="Cross",
        family_name="Patient",
        date_of_birth=date(2000, 1, 1),
        identity_status="unverified",
    )
    db_session.add(other_patient)
    db_session.commit()
    cross_supersession = client.post(
        "/api/v1/conditions",
        headers=headers(hospital),
        auth=AUTH,
        json={
            "patient_id": str(other_patient.id),
            "provenance_id": provenance["id"],
            "display_name": "Cross supersession",
            "status": "active",
            "verification_status": "verified",
            "superseded_by_condition_id": first_condition["id"],
        },
    )
    assert cross_supersession.status_code == 409
