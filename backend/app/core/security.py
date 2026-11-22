import base64
import binascii
import hashlib
import hmac
import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.hospital_user import HospitalUser
from app.models.user import User


_PBKDF2_ALGORITHM = "sha256"
_PBKDF2_ITERATIONS = 600_000
_PASSWORD_HASH_PARTS = 4


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password is required")

    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        _PBKDF2_ALGORITHM,
        password.encode("utf-8"),
        salt,
        _PBKDF2_ITERATIONS,
    )
    return (
        f"pbkdf2_{_PBKDF2_ALGORITHM}"
        f"${_PBKDF2_ITERATIONS}"
        f"${base64.b64encode(salt).decode('ascii')}"
        f"${base64.b64encode(digest).decode('ascii')}"
    )


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password or not password_hash:
        return False

    parts = password_hash.split("$")
    if len(parts) != _PASSWORD_HASH_PARTS:
        return False

    algorithm_label, iterations_text, salt_text, digest_text = parts
    if algorithm_label != f"pbkdf2_{_PBKDF2_ALGORITHM}":
        return False

    try:
        iterations = int(iterations_text)
        salt = base64.b64decode(salt_text, validate=True)
        expected_digest = base64.b64decode(digest_text, validate=True)
    except (ValueError, binascii.Error):
        return False

    actual_digest = hashlib.pbkdf2_hmac(
        _PBKDF2_ALGORITHM,
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual_digest, expected_digest)


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == email))
    if user is None or user.status != "active":
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_active_hospital_assignments(
    db: Session,
    user: User,
) -> list[HospitalUser]:
    now = datetime.now(timezone.utc)
    assignments = list(
        db.scalars(
            select(HospitalUser).where(
                HospitalUser.user_id == user.id,
                HospitalUser.status == "active",
            )
        )
    )
    active_assignments = []
    for assignment in assignments:
        valid_from = assignment.valid_from
        if valid_from.tzinfo is None:
            valid_from = valid_from.replace(tzinfo=timezone.utc)

        valid_until = assignment.valid_until
        if valid_until is not None and valid_until.tzinfo is None:
            valid_until = valid_until.replace(tzinfo=timezone.utc)

        if valid_from <= now and (
            valid_until is None or valid_until >= now
        ):
            active_assignments.append(assignment)
    return active_assignments


def find_active_hospital_assignment(
    assignments: list[HospitalUser],
    hospital_id,
) -> HospitalUser | None:
    return next(
        (
            assignment
            for assignment in assignments
            if assignment.hospital_id == hospital_id
        ),
        None,
    )


def require_role_codes(
    assignment: HospitalUser,
    allowed_role_codes: tuple[str, ...],
) -> bool:
    if not allowed_role_codes:
        return True
    return assignment.role_code in allowed_role_codes


def validate_legitimate_purpose(purpose: str | None) -> bool:
    if purpose is None:
        return False
    normalized = purpose.strip()
    return 1 <= len(normalized) <= 128


def validate_patient_object_access(
    assignment: HospitalUser,
    patient_id,
) -> bool:
    if patient_id is None:
        return False
    if assignment.relationship_scope == "hospital":
        return True
    # Department and patient_relationship scopes require a relationship
    # table that is not implemented or approved in this MVP. Fail closed.
    return False
