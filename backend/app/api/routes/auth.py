from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import (
    authenticate_user,
    get_active_hospital_assignments,
    find_active_hospital_assignment,
    validate_legitimate_purpose,
)
from app.db.session import get_db


router = APIRouter(prefix="/auth", tags=["authentication"])
basic_security = HTTPBasic()


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)


class HospitalAssignmentResponse(BaseModel):
    hospital_user_id: UUID
    hospital_id: UUID
    role_code: str
    relationship_scope: str


class CurrentUserResponse(BaseModel):
    user_id: UUID
    email: str | None
    display_name: str
    assignments: list[HospitalAssignmentResponse]


class LoginResponse(CurrentUserResponse):
    pass


def get_current_user(
    credentials: HTTPBasicCredentials = Depends(basic_security),
    db: Session = Depends(get_db),
) -> tuple:
    user = authenticate_user(db, credentials.username, credentials.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return user, db


def build_current_user_response(
    user,
    db: Session,
) -> CurrentUserResponse:
    assignments = get_active_hospital_assignments(db, user)
    return CurrentUserResponse(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        assignments=[
            HospitalAssignmentResponse(
                hospital_user_id=assignment.id,
                hospital_id=assignment.hospital_id,
                role_code=assignment.role_code,
                relationship_scope=assignment.relationship_scope,
            )
            for assignment in assignments
        ],
    )


@router.post("/login", response_model=LoginResponse)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
) -> LoginResponse:
    user = authenticate_user(db, request.email, request.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return LoginResponse.model_validate(
        build_current_user_response(user, db).model_dump()
    )


@router.get("/me", response_model=CurrentUserResponse)
def me(
    x_hospital_id: UUID = Header(),
    x_legitimate_purpose: str | None = Header(
        default=None,
        alias="X-Mediflow-Purpose",
    ),
    auth=Depends(get_current_user),
) -> CurrentUserResponse:
    user, db = auth
    if not validate_legitimate_purpose(x_legitimate_purpose):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Mediflow-Purpose is required",
        )
    response = build_current_user_response(user, db)
    active_assignments = get_active_hospital_assignments(db, user)
    assignment = find_active_hospital_assignment(
        active_assignments,
        x_hospital_id,
    )
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active assignment in the requested hospital",
        )
    response.assignments = [
        selected_assignment
        for selected_assignment in response.assignments
        if selected_assignment.hospital_id == x_hospital_id
    ]
    return response
