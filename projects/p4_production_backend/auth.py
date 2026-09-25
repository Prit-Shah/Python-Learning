"""
Project P4: JWT Authentication & Role-Based Access Control
"""
from datetime import datetime, timezone, timedelta
import hashlib
import hmac
import json
import base64
from typing import Any
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .config import settings

security = HTTPBearer()


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * (4 - (len(data) % 4)) if len(data) % 4 != 0 else ""
    return base64.urlsafe_b64decode((data + padding).encode("utf-8"))


def create_access_token(subject: str, role: str = "user", expires_delta: timedelta | None = None) -> str:
    """Creates a signed HMAC-SHA256 JWT access token."""
    header = {"alg": "HS256", "typ": "JWT"}
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_expiration_minutes)
    )
    payload = {
        "sub": subject,
        "role": role,
        "exp": int(expire.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
    }

    hdr_b64 = _base64url_encode(json.dumps(header).encode("utf-8"))
    pay_b64 = _base64url_encode(json.dumps(payload).encode("utf-8"))
    msg = f"{hdr_b64}.{pay_b64}".encode("utf-8")

    sig = hmac.new(settings.jwt_secret_key.encode("utf-8"), msg, hashlib.sha256).digest()
    sig_b64 = _base64url_encode(sig)

    return f"{hdr_b64}.{pay_b64}.{sig_b64}"


def decode_access_token(token: str) -> dict[str, Any]:
    """Validates and decodes HMAC-SHA256 JWT signature and claims."""
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid JWT structure",
        )

    hdr_b64, pay_b64, sig_b64 = parts
    msg = f"{hdr_b64}.{pay_b64}".encode("utf-8")
    expected_sig = hmac.new(settings.jwt_secret_key.encode("utf-8"), msg, hashlib.sha256).digest()
    actual_sig = _base64url_decode(sig_b64)

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid JWT cryptographic signature",
        )

    payload = json.loads(_base64url_decode(pay_b64).decode("utf-8"))
    if datetime.now(timezone.utc).timestamp() > payload["exp"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT token has expired",
        )

    return payload


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Any]:
    """FastAPI Dependency extracting authenticated user claims."""
    return decode_access_token(credentials.credentials)


def require_role(required_role: str):
    """Role-Based Access Control dependency factory."""
    def _role_checker(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        if user.get("role") != required_role and user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires '{required_role}' privileges",
            )
        return user
    return _role_checker
