from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user
from app.core.security import (
    find_active_hospital_assignment,
    get_active_hospital_assignments,
    require_role_codes,
    validate_legitimate_purpose,
    validate_patient_object_access,
)
from app.db.session import get_db


@dataclass(frozen=True)
class AuthorizationContext:
    user: object
    db: Session
    assignment: object
    hospital_id: UUID
    purpose: str


def authorize(
    x_hospital_id: UUID = Header(),
    x_mediflow_purpose: str | None = Header(
        default=None,
        alias="X-Mediflow-Purpose",
    ),
    auth=Depends(get_current_user),
) -> AuthorizationContext:
    user, db = auth
    if not validate_legitimate_purpose(x_mediflow_purpose):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Mediflow-Purpose is required",
        )
    assignments = get_active_hospital_assignments(db, user)
    assignment = find_active_hospital_assignment(
        assignments,
        x_hospital_id,
    )
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active assignment in the requested hospital",
        )
    return AuthorizationContext(
        user=user,
        db=db,
        assignment=assignment,
        hospital_id=x_hospital_id,
        purpose=x_mediflow_purpose,
    )


def require_roles(*role_codes: str):
    allowed_role_codes = tuple(role_codes)

    def dependency(
        context: AuthorizationContext = Depends(authorize),
    ) -> AuthorizationContext:
        if not require_role_codes(context.assignment, allowed_role_codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Role is not permitted for this operation",
            )
        return context

    return dependency


def require_patient_object_access(
    context: AuthorizationContext,
    patient_id,
) -> None:
    if not validate_patient_object_access(context.assignment, patient_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No approved patient relationship for this operation",
        )
