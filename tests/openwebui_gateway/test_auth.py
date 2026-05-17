"""Tests for openwebui_gateway.auth JWT authentication module."""

import os
import time
from datetime import datetime, timedelta

import jwt
import pytest


@pytest.fixture(autouse=True)
def isolate_admin_secret(monkeypatch):
    """Isolate ADMIN_SECRET so tests don't leak to each other."""
    monkeypatch.setenv("ADMIN_SECRET", "test_secret")
    # Force re-import to pick up new env var
    import importlib

    import openwebui_gateway.auth

    importlib.reload(openwebui_gateway.auth)


class TestCreateAdminToken:
    def test_returns_jwt_string(self, isolate_admin_secret):
        from openwebui_gateway.auth import create_admin_token

        token = create_admin_token("admin@example.com")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_contains_user_id(self, isolate_admin_secret):
        from openwebui_gateway.auth import ADMIN_SECRET, JWT_ALGORITHM, create_admin_token

        token = create_admin_token("admin@example.com")
        payload = jwt.decode(token, ADMIN_SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["user_id"] == "admin@example.com"

    def test_contains_admin_role(self, isolate_admin_secret):
        from openwebui_gateway.auth import ADMIN_SECRET, JWT_ALGORITHM, create_admin_token

        token = create_admin_token("admin@example.com")
        payload = jwt.decode(token, ADMIN_SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["role"] == "admin"

    def test_expiry_is_7_days(self, isolate_admin_secret):
        from openwebui_gateway.auth import ADMIN_SECRET, JWT_ALGORITHM, create_admin_token

        token = create_admin_token("admin@example.com")
        payload = jwt.decode(token, ADMIN_SECRET, algorithms=[JWT_ALGORITHM], options={"verify_exp": False})
        exp = datetime.utcfromtimestamp(payload["exp"])
        now = datetime.utcnow()
        delta = exp - now
        assert 6 <= delta.days <= 7


class TestVerifyAdminToken:
    def test_valid_token_returns_true(self, isolate_admin_secret):
        from openwebui_gateway.auth import create_admin_token, verify_admin_token

        token = create_admin_token("admin@example.com")
        assert verify_admin_token(token) is True

    def test_expired_token_returns_false(self, isolate_admin_secret):
        from openwebui_gateway.auth import ADMIN_SECRET, JWT_ALGORITHM, verify_admin_token

        payload = {
            "user_id": "admin@example.com",
            "role": "admin",
            "exp": datetime.utcnow() - timedelta(hours=1),
        }
        token = jwt.encode(payload, ADMIN_SECRET, algorithm=JWT_ALGORITHM)
        assert verify_admin_token(token) is False

    def test_invalid_token_returns_false(self, isolate_admin_secret):
        from openwebui_gateway.auth import verify_admin_token

        assert verify_admin_token("not.a.jwt") is False

    def test_empty_token_returns_false(self, isolate_admin_secret):
        from openwebui_gateway.auth import verify_admin_token

        assert verify_admin_token("") is False

    def test_wrong_secret_returns_false(self, isolate_admin_secret):
        from openwebui_gateway.auth import create_admin_token, verify_admin_token

        token = create_admin_token("admin@example.com")
        # Tamper the token by re-encoding with a different secret
        payload = jwt.decode(token, "test_secret", algorithms=["HS256"])
        tampered = jwt.encode(payload, "wrong_secret", algorithm="HS256")
        assert verify_admin_token(tampered) is False

    def test_non_admin_role_returns_false(self, isolate_admin_secret):
        from openwebui_gateway.auth import ADMIN_SECRET, JWT_ALGORITHM, verify_admin_token

        payload = {
            "user_id": "user@example.com",
            "role": "user",
            "exp": datetime.utcnow() + timedelta(days=7),
        }
        token = jwt.encode(payload, ADMIN_SECRET, algorithm=JWT_ALGORITHM)
        assert verify_admin_token(token) is False


class TestGetUserIdFromOpenwebuiToken:
    def test_valid_token_returns_sub(self, isolate_admin_secret):
        from openwebui_gateway.auth import ADMIN_SECRET, JWT_ALGORITHM, get_user_id_from_openwebui_token

        payload = {
            "sub": "user@example.com",
            "exp": datetime.utcnow() + timedelta(days=7),
        }
        token = jwt.encode(payload, ADMIN_SECRET, algorithm=JWT_ALGORITHM)
        assert get_user_id_from_openwebui_token(token) == "user@example.com"

    def test_invalid_token_returns_none(self, isolate_admin_secret):
        from openwebui_gateway.auth import get_user_id_from_openwebui_token

        assert get_user_id_from_openwebui_token("invalid") is None

    def test_missing_sub_returns_none(self, isolate_admin_secret):
        from openwebui_gateway.auth import ADMIN_SECRET, JWT_ALGORITHM, get_user_id_from_openwebui_token

        payload = {
            "user_id": "admin@example.com",
            "exp": datetime.utcnow() + timedelta(days=7),
        }
        token = jwt.encode(payload, ADMIN_SECRET, algorithm=JWT_ALGORITHM)
        assert get_user_id_from_openwebui_token(token) is None


class TestVerifyToken:
    def test_valid_token_returns_payload(self, isolate_admin_secret):
        from openwebui_gateway.auth import create_admin_token, verify_token

        token = create_admin_token("admin@example.com")
        payload = verify_token(token)
        assert payload is not None
        assert payload["user_id"] == "admin@example.com"
        assert payload["role"] == "admin"

    def test_invalid_token_returns_none(self, isolate_admin_secret):
        from openwebui_gateway.auth import verify_token

        assert verify_token("garbage") is None

    def test_expired_token_returns_none(self, isolate_admin_secret):
        from openwebui_gateway.auth import ADMIN_SECRET, JWT_ALGORITHM, verify_token

        payload = {
            "user_id": "admin@example.com",
            "role": "admin",
            "exp": datetime.utcnow() - timedelta(hours=1),
        }
        token = jwt.encode(payload, ADMIN_SECRET, algorithm=JWT_ALGORITHM)
        assert verify_token(token) is None


class TestAdminSecret:
    def test_default_secret(self):
        """Verify default fallback when ADMIN_SECRET is not set."""
        import importlib
        import openwebui_gateway.auth

        # Temporarily unset
        old = os.environ.pop("ADMIN_SECRET", None)
        importlib.reload(openwebui_gateway.auth)
        try:
            assert openwebui_gateway.auth.ADMIN_SECRET == "cyan_default_secret"
        finally:
            if old is not None:
                os.environ["ADMIN_SECRET"] = old
            else:
                os.environ.pop("ADMIN_SECRET", None)
            importlib.reload(openwebui_gateway.auth)

    def test_env_override(self, monkeypatch):
        """Verify env var overrides default."""
        monkeypatch.setenv("ADMIN_SECRET", "custom_secret")
        import importlib
        import openwebui_gateway.auth

        importlib.reload(openwebui_gateway.auth)
        assert openwebui_gateway.auth.ADMIN_SECRET == "custom_secret"
