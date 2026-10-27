from __future__ import annotations

import datetime as dt
import hmac

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import DEFAULT_APP_PASSWORD, DEFAULT_JWT_SECRET, Settings, get_settings
from app.core.logging import get_logger

_bearer = HTTPBearer(auto_error=False)
logger = get_logger(__name__)


class InsecureSettingsError(RuntimeError):
    """Geliştirme dışı bir ortamda varsayılan (herkesçe bilinen) gizli değerler."""


def assert_secure_settings(settings: Settings) -> None:
    """Uygulama açılışında çağrılır (ADR-007).

    Geliştirme dışında varsayılan JWT anahtarı veya varsayılan parola ile
    açılmayı reddeder — ayarsız bir kurulum sessizce herkese açık kalmasın.
    Geliştirmede bypass açıksa bunu yüksek sesle loglar.
    """
    if settings.app_env != "development":
        problems = []
        if settings.jwt_secret == DEFAULT_JWT_SECRET:
            problems.append("JWT_SECRET")
        if settings.app_user_password == DEFAULT_APP_PASSWORD:
            problems.append("APP_USER_PASSWORD")
        if problems:
            raise InsecureSettingsError(
                f"Güvensiz yapılandırma ({settings.app_env}): {', '.join(problems)} varsayılan değerde. "
                ".env dosyasında gerçek değerler tanımlayın."
            )
    elif settings.auth_dev_bypass:
        logger.warning("auth_dev_bypass_active: kimlik doğrulama kapalı (yalnızca geliştirme)")


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
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Bearer token eksik")
    try:
        payload = jwt.decode(
            credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Geçersiz token") from exc
    return payload.get("sub", "")
