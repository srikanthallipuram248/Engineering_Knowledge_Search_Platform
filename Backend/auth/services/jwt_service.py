from datetime import datetime, timedelta, timezone

from jose import jwt

SECRET_KEY = "CHANGE_ME"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


class JWTService:

    @staticmethod
    def create_access_token(
        user_id: str,
        email: str,
    ) -> str:

        expire = (
            datetime.now(timezone.utc)
            + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        payload = {
            "sub": user_id,
            "email": email,
            "exp": expire,
        }

        return jwt.encode(
            payload,
            SECRET_KEY,
            algorithm=ALGORITHM,
        )