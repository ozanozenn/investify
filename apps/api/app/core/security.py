from __future__ import annotations

import datetime as dt
import hmac

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import Settings, get_settings

_bearer = HTTPBearer(auto_error=False)


def create_access_token(subject: str, settings: Settings) -> str:
    expire = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_credentials(email: str, password: str, settings: Settings) -> bool:
    return hmac.compare_digest(email, settings.app_user_email) and hmac.compare_digest(
        password, settings.app_user_password
    )


async def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> str:
    """Single-user auth (roadmap section 45): JWT bearer token, with a local
    dev bypass so `docker compose up` works before anyone logs in.
    """
    if settings.auth_dev_bypass and settings.app_env == "development":
        return settings.app_user_email

    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    try:
        payload = jwt.decode(
            credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    return payload.get("sub", "")
