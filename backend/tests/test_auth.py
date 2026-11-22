from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session

from app.core.security import (
    find_active_hospital_assignment,
    hash_password,
    require_role_codes,
    validate_legitimate_purpose,
    validate_patient_object_access,
    verify_password,
)
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Hospital, HospitalUser, User


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


def make_account(
    db: Session,
    *,
    status: str = "active",
    role_code: str = "doctor",
) -> tuple[User, Hospital, HospitalUser]:
    hospital = Hospital(name="Synthetic General Hospital", code="SYN-1")
    db.add(hospital)
    db.flush()
    user = User(
        email="doctor.synthetic@example.test",
        display_name="Synthetic Doctor",
        status=status,
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
    return user, hospital, assignment


def test_password_hash_is_salted_and_verifies(client, db_session):
    first = hash_password("Synthetic-Password-123")
    second = hash_password("Synthetic-Password-123")

    assert first != second
    assert verify_password("Synthetic-Password-123", first)
    assert not verify_password("wrong-password", first)
    assert not verify_password("Synthetic-Password-123", None)


def test_login_returns_active_hospital_assignment(client, db_session):
    user, hospital, assignment = make_account(db_session)

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "doctor.synthetic@example.test",
            "password": "Synthetic-Password-123",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == str(user.id)
    assert body["email"] == "doctor.synthetic@example.test"
    assert body["assignments"] == [
        {
            "hospital_user_id": str(assignment.id),
            "hospital_id": str(hospital.id),
            "role_code": "doctor",
            "relationship_scope": "hospital",
        }
    ]


def test_login_rejects_wrong_password(client, db_session):
    make_account(db_session)

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "doctor.synthetic@example.test",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_rejects_disabled_user(client, db_session):
    make_account(db_session, status="disabled")

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "doctor.synthetic@example.test",
            "password": "Synthetic-Password-123",
        },
    )

    assert response.status_code == 401


def test_http_basic_me_requires_valid_credentials_and_hospital_assignment(
    client,
    db_session,
):
    user, hospital, _assignment = make_account(db_session)

    response = client.get(
        "/api/v1/auth/me",
        headers={
            "X-Hospital-Id": str(hospital.id),
            "X-Mediflow-Purpose": "synthetic account verification",
        },
        auth=("doctor.synthetic@example.test", "Synthetic-Password-123"),
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == str(user.id)
    assert len(response.json()["assignments"]) == 1

    wrong_password = client.get(
        "/api/v1/auth/me",
        headers={
            "X-Hospital-Id": str(hospital.id),
            "X-Mediflow-Purpose": "synthetic account verification",
        },
        auth=("doctor.synthetic@example.test", "wrong-password"),
    )
    assert wrong_password.status_code == 401


def test_http_basic_me_rejects_hospital_without_active_assignment(
    client,
    db_session,
):
    make_account(db_session)
    other_hospital = Hospital(name="Other Synthetic Hospital", code="SYN-2")
    db_session.add(other_hospital)
    db_session.commit()

    response = client.get(
        "/api/v1/auth/me",
        headers={
            "X-Hospital-Id": str(other_hospital.id),
            "X-Mediflow-Purpose": "synthetic account verification",
        },
        auth=("doctor.synthetic@example.test", "Synthetic-Password-123"),
    )

    assert response.status_code == 403


def test_me_requires_legitimate_purpose_header(client, db_session):
    make_account(db_session)

    response = client.get(
        "/api/v1/auth/me",
        headers={"X-Hospital-Id": str(db_session.query(Hospital).one().id)},
        auth=("doctor.synthetic@example.test", "Synthetic-Password-123"),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "X-Mediflow-Purpose is required"


def test_exact_role_code_enforcement(client, db_session):
    _user, hospital, assignment = make_account(
        db_session,
        role_code="pharmacist",
    )

    active_assignment = find_active_hospital_assignment(
        [assignment],
        hospital.id,
    )
    assert active_assignment is assignment
    assert require_role_codes(assignment, ("pharmacist",))
    assert not require_role_codes(assignment, ("doctor",))


def test_legitimate_purpose_validation_rejects_empty_or_overlong_value():
    assert not validate_legitimate_purpose(None)
    assert not validate_legitimate_purpose("")
    assert not validate_legitimate_purpose("   ")
    assert not validate_legitimate_purpose("x" * 129)
    assert validate_legitimate_purpose("treatment")


def test_patient_object_access_is_hospital_scope_or_fail_closed(db_session):
    hospital = Hospital(name="Synthetic scope hospital", code="SCOPE")
    db_session.add(hospital)
    db_session.flush()
    user = User(
        email="scope.synthetic@example.test",
        display_name="Synthetic Scope",
        status="active",
        password_hash=hash_password("Synthetic-Password-123"),
    )
    db_session.add(user)
    db_session.flush()

    hospital_assignment = HospitalUser(
        hospital=hospital,
        user=user,
        role_code="doctor",
        relationship_scope="hospital",
        status="active",
        valid_from=datetime(2026, 11, 22, tzinfo=timezone.utc),
    )
    restricted_assignment = HospitalUser(
        hospital=hospital,
        user=user,
        role_code="doctor",
        relationship_scope="patient_relationship",
        status="active",
        valid_from=datetime(2026, 11, 22, tzinfo=timezone.utc),
    )
    db_session.add_all([hospital_assignment, restricted_assignment])

    patient_id = uuid4()
    assert validate_patient_object_access(hospital_assignment, patient_id)
    assert not validate_patient_object_access(restricted_assignment, patient_id)
    assert not validate_patient_object_access(hospital_assignment, None)
