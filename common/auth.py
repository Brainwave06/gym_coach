"""
Authentication and security utilities for FitPath / Gym AI.
Provides RFC 7519 HMAC-SHA256 JWT generation/verification and salted PBKDF2 password hashing.
Zero external C-dependencies for 100% reliable cross-platform execution.
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("gym_ai.auth")

SECRET_KEY = os.getenv("FITPATH_JWT_SECRET", "fitpath-secure-super-secret-key-2026-gym-ai")
TOKEN_EXPIRY_HOURS = int(os.getenv("FITPATH_TOKEN_EXPIRY_HOURS", "72"))
PBKDF2_ITERATIONS = 100_000


def _b64url_encode(data: bytes) -> str:
    """Encode bytes to base64url string without trailing padding."""
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    """Decode base64url string with flexible padding."""
    rem = len(s) % 4
    if rem > 0:
        s += "=" * (4 - rem)
    return base64.urlsafe_b64decode(s.encode("utf-8"))


def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """
    Hash a plaintext password using PBKDF2-HMAC-SHA256 with a unique random salt.
    Returns (hashed_password_hex, salt_hex).
    """
    if not salt:
        salt = secrets.token_hex(16)
    hashed_bytes = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return hashed_bytes.hex(), salt


def verify_password(password: str, hashed: str, salt: str) -> bool:
    """Verify a plaintext password against a stored PBKDF2-HMAC-SHA256 hash."""
    expected_hash, _ = hash_password(password, salt=salt)
    return hmac.compare_digest(expected_hash, hashed)


def create_access_token(
    data: Dict[str, Any],
    expires_delta_hours: int = TOKEN_EXPIRY_HOURS,
) -> str:
    """
    Create a standard RFC 7519 HS256 JWT access token.
    """
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        **data,
        "iat": now,
        "exp": now + (expires_delta_hours * 3600),
    }

    header_bytes = json.dumps(header, separators=(",", ":")).encode("utf-8")
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    enc_header = _b64url_encode(header_bytes)
    enc_payload = _b64url_encode(payload_bytes)

    signing_input = f"{enc_header}.{enc_payload}".encode("utf-8")
    signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    enc_signature = _b64url_encode(signature)

    return f"{enc_header}.{enc_payload}.{enc_signature}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Validate and decode an HS256 JWT access token.
    Returns decoded payload if signature and expiration are valid, else None.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        enc_header, enc_payload, enc_signature = parts
        signing_input = f"{enc_header}.{enc_payload}".encode("utf-8")

        expected_sig = hmac.new(
            SECRET_KEY.encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).digest()

        actual_sig = _b64url_decode(enc_signature)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload_bytes = _b64url_decode(enc_payload)
        payload = json.loads(payload_bytes.decode("utf-8"))

        # Expiration check
        exp = payload.get("exp")
        if exp and int(exp) < int(time.time()):
            return None

        return payload
    except Exception as exc:
        logger.debug(f"JWT decode failed: {exc}")
        return None


def get_current_user_from_header(auth_header: Optional[str]) -> Optional[Dict[str, Any]]:
    """Extract and verify user payload from Authorization: Bearer <token> header."""
    if not auth_header:
        return None
    parts = auth_header.strip().split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return decode_access_token(parts[1])
    return None
