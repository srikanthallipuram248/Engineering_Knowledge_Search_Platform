from sqlalchemy.orm import Session

from auth.schemas.user_request import (
    RegisterRequest,
    LoginRequest,
)
from auth.services.auth_service import AuthService


class AuthController:

    @staticmethod
    def register(
        payload: RegisterRequest,
        db: Session,
    ):
        return AuthService.register(
            db,
            payload,
        )

    @staticmethod
    def login(
        payload: LoginRequest,
        db: Session,
    ):
        return AuthService.login(
            db,
            payload,
        )