import pytest

from app.core.config import DEFAULT_APP_PASSWORD, DEFAULT_JWT_SECRET, Settings
from app.core.security import InsecureSettingsError, assert_secure_settings


def test_bypass_is_off_by_default():
    assert Settings(_env_file=None).auth_dev_bypass is False


def test_production_with_default_secrets_refuses_to_start():
    with pytest.raises(InsecureSettingsError) as exc:
        assert_secure_settings(Settings(_env_file=None, app_env="production"))
    assert "JWT_SECRET" in str(exc.value) and "APP_USER_PASSWORD" in str(exc.value)


def test_production_with_real_secrets_starts():
    assert_secure_settings(
        Settings(
            _env_file=None, app_env="production", jwt_secret="gercek-bir-anahtar", app_user_password="guclu-sifre"
        )
    )


def test_development_allows_defaults():
    s = Settings(_env_file=None, app_env="development")
    assert s.jwt_secret == DEFAULT_JWT_SECRET and s.app_user_password == DEFAULT_APP_PASSWORD
    assert_secure_settings(s)  # geliştirmede yalnızca uyarı
