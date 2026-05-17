"""JWT authentication for Cyan Agent admin endpoints."""

import os
from datetime import datetime, timedelta
from typing import Optional

import jwt

# Read admin secret from environment
ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "cyan_default_secret")
JWT_ALGORITHM = "HS256"


def create_admin_token(user_id: str) -> str:
    """Create admin JWT token with 7-day expiry."""
    payload = {
        "user_id": user_id,
        "role": "admin",
        "exp": datetime.utcnow() + timedelta(days=7),
    }
    return jwt.encode(payload, ADMIN_SECRET, algorithm=JWT_ALGORITHM)


def verify_admin_token(token: str) -> bool:
    """Verify an admin JWT token.

    Returns True for valid admin tokens, False for expired/invalid tokens.
    """
    try:
        payload = jwt.decode(token, ADMIN_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("role") == "admin"
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return False


def get_user_id_from_openwebui_token(token: str) -> Optional[str]:
    """Extract user_id (sub claim) from an Open-WebUI token."""
    try:
        payload = jwt.decode(token, ADMIN_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def verify_token(token: str) -> Optional[dict]:
    """Generic token verification.

    Returns the full payload dict or None.
    """
    try:
        return jwt.decode(token, ADMIN_SECRET, algorithms=[JWT_ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
