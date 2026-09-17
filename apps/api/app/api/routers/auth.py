from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.core.security import create_access_token, verify_credentials
from app.schemas.api import LoginRequest, LoginResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, settings: Settings = Depends(get_settings)):
    if not verify_credentials(payload.email, payload.password, settings):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Geçersiz kullanıcı adı veya şifre")
    token = create_access_token(payload.email, settings)
    return LoginResponse(access_token=token)
