from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.schemas.user_request import (
    RegisterRequest,
    LoginRequest,
)
from auth.services.jwt_service import JWTService
from auth.services.password_service import PasswordService

from database.postgres.models.user import User


class AuthService:

    @staticmethod
    def register(
        db: Session,
        payload: RegisterRequest,
    ):

        existing_user = db.scalar(
            select(User).where(
                User.email == payload.email
            )
        )

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exists",
            )

        user = User(
            email=payload.email,
            hashed_password=PasswordService.hash_password(
                payload.password
            ),
            full_name=payload.full_name,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        token = JWTService.create_access_token(
            str(user.id),
            user.email,
        )

        return {
            "access_token": token,
            "user": user,
        }

    @staticmethod
    def login(
        db: Session,
        payload: LoginRequest,
    ):

        user = db.scalar(
            select(User).where(
                User.email == payload.email
            )
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        if not PasswordService.verify_password(
            payload.password,
            user.hashed_password,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        token = JWTService.create_access_token(
            str(user.id),
            user.email,
        )

        return {
            "access_token": token,
            "user": user,
        }