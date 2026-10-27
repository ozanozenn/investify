import pytest

from app.core.config import Settings, get_settings
from app.main import app


_SETTINGS = Settings(
    _env_file=None, auth_dev_bypass=False, app_env="development", app_user_password="test-sifre"
)


@pytest.fixture
def auth_on(client):
    # conftest bypass'ı açık veriyor; burada üretimdeki gibi kapalı.
    app.dependency_overrides[get_settings] = lambda: _SETTINGS
    yield client


@pytest.mark.asyncio
async def test_protected_route_needs_token_when_bypass_off(auth_on):
    resp = await auth_on.get("/api/companies/search", params={"q": "THY"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Bearer token eksik"


@pytest.mark.asyncio
async def test_login_then_token_grants_access(auth_on):
    settings = _SETTINGS
    bad = await auth_on.post("/api/auth/login", json={"email": settings.app_user_email, "password": "yanlis"})
    assert bad.status_code == 401

    ok = await auth_on.post(
        "/api/auth/login", json={"email": settings.app_user_email, "password": settings.app_user_password}
    )
    assert ok.status_code == 200
    token = ok.json()["access_token"]

    resp = await auth_on.get(
        "/api/companies/search", params={"q": "THY"}, headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
