from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth.controllers.auth_controller import AuthController

from auth.schemas.user_request import (
    RegisterRequest,
    LoginRequest,
)

from auth.schemas.user_response import (
    AuthResponse,
    UserResponse,
)

from database.postgres.session import get_db

router = APIRouter(
    tags=["Authentication"]
)


@router.post(
    "/register",
    response_model=AuthResponse,
)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
):

    result = AuthController.register(
        payload,
        db,
    )

    return {
        "access_token": result["access_token"],
        "user": UserResponse.model_validate(
            result["user"]
        ),
    }


@router.post(
    "/login",
    response_model=AuthResponse,
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):

    result = AuthController.login(
        payload,
        db,
    )

    return {
        "access_token": result["access_token"],
        "user": UserResponse.model_validate(
            result["user"]
        ),
    }