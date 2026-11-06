import pytest
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.core.security import create_access_token, decode_access_token


def test_settings_require_a_non_placeholder_jwt_secret(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)

    with pytest.raises(ValidationError):
        Settings(_env_file=None, jwt_secret="replace-with-a-long-random-secret")

    with pytest.raises(ValidationError):
        Settings(_env_file=None, jwt_secret="replace-this-with-a-random-secret-of-at-least-32-characters")


def test_production_requires_secure_cookies():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, jwt_secret="a" * 48, app_env="production", secure_cookie=False)

    settings = Settings(_env_file=None, jwt_secret="a" * 48, app_env="production", secure_cookie=True)
    assert settings.secure_cookie is True


def test_registration_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ALLOW_REGISTRATION", raising=False)
    settings = Settings(_env_file=None, jwt_secret="a" * 48)
    assert settings.allow_registration is False


def test_generated_style_secret_may_contain_uppercase():
    settings = Settings(_env_file=None, jwt_secret="AbC9_xYz" * 6)
    assert settings.jwt_secret == "AbC9_xYz" * 6


def test_expired_jwt_is_rejected(monkeypatch):
    monkeypatch.setattr(settings, "access_token_minutes", -1)
    token = create_access_token("00000000-0000-0000-0000-000000000001")
    assert decode_access_token(token) is None


def test_logout_clears_cookie_but_does_not_revoke_a_copied_token(client):
    registered = client.post("/api/v1/auth/register", json={
        "email": "logout@example.com", "full_name": "Logout Test", "password": "secure-logout-test-password",
    })
    assert registered.status_code == 201
    cookie_header = registered.headers["set-cookie"].lower()
    assert "httponly" in cookie_header
    assert "samesite=lax" in cookie_header
    copied_token = client.cookies.get("pace_access")
    assert copied_token

    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401
    client.cookies.set("pace_access", copied_token)
    assert client.get("/api/v1/auth/me").status_code == 200