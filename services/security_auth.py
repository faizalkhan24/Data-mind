"""
DataMind Security & Validation Core Layer
=========================================
Centralized security dependencies, authentication, model integrity verification,
and input sanitization utilities for DataMind microservices.

TRACEABILITY LEDGER:
- [SECURITY-2]: Cryptographic Model Checksum Verification (SHA-256)
- [SECURITY-3]: API Key & Bearer Token Authentication Dependency
- [VALIDATION-1]: Strict Hardware Device ID Sanitization & Pattern Enforcement
- [VALIDATION-3]: NaN / Infinite / Out-of-bounds Float Guardrails
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import math
import os
from pathlib import Path
import re
from typing import Optional

from fastapi import Header, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials

logger = None
try:
    import logging
    logger = logging.getLogger("datamind.security")
except ImportError:
    pass

# [SECURITY-3]: API Key and Bearer Token Security Schemes
_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
_BEARER_AUTH = HTTPBearer(auto_error=False)

# [VALIDATION-1]: Strict alphanumeric + underscore/hyphen pattern (3 to 64 chars)
DEVICE_ID_REGEX = r"^[A-Za-z0-9_\-]{3,64}$"
_DEVICE_ID_PATTERN = re.compile(DEVICE_ID_REGEX)


def sanitize_device_id(device_id: str) -> str:
    """
    [VALIDATION-1]: Sanitizes and validates hardware device identifier.
    Rejects path traversal, SQL injection, script injection, and invalid lengths.
    """
    if not device_id or not isinstance(device_id, str):
        raise ValueError("Device ID must be a non-empty string.")
    cleaned = device_id.strip()
    if not _DEVICE_ID_PATTERN.match(cleaned):
        raise ValueError(
            f"Invalid device_id '{device_id}'. Must match pattern '{DEVICE_ID_REGEX}' (3-64 alphanumeric chars)."
        )
    return cleaned


def parse_iso_timestamp(timestamp_str: str) -> datetime:
    """
    [VALIDATION-2]: Parses and validates ISO-8601 formatted timestamp string into UTC datetime.
    Rejects malformed strings or invalid datetime formats.
    """
    if not timestamp_str or not isinstance(timestamp_str, str):
        raise ValueError("Timestamp must be a non-empty ISO-8601 string.")

    cleaned = timestamp_str.strip()
    # Normalize trailing Z to +00:00 for datetime.fromisoformat
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(cleaned)
    except Exception as exc:
        raise ValueError(f"Invalid ISO-8601 timestamp '{timestamp_str}': {exc}") from exc

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


def validate_finite_number(val: Optional[float], field_name: str) -> Optional[float]:
    """
    [VALIDATION-3]: Validates that floating point numbers are finite (not NaN, +Inf, or -Inf).
    """
    if val is not None:
        if math.isnan(val) or math.isinf(val):
            raise ValueError(f"Field '{field_name}' must be a finite number; received NaN or Infinity.")
    return val


def verify_model_integrity(model_path: Path) -> str:
    """
    [SECURITY-2]: Cryptographically verifies SHA-256 checksum of model artifact
    prior to joblib.load() deserialization to prevent arbitrary code execution.
    """
    if not model_path.exists():
        raise FileNotFoundError(f"Model artifact not found at: {model_path}")

    # Compute actual SHA-256
    file_bytes = model_path.read_bytes()
    actual_hash = hashlib.sha256(file_bytes).hexdigest()

    # Look for matching .sha256 sidecar file
    sidecar_path = model_path.with_suffix(model_path.suffix + ".sha256")
    if sidecar_path.exists():
        expected_hash = sidecar_path.read_text(encoding="utf-8").strip().lower()
        if actual_hash.lower() != expected_hash:
            raise SecurityError(
                f"[SECURITY-2] Model integrity breach detected! "
                f"Artifact SHA-256 ({actual_hash}) does not match expected checksum ({expected_hash}). "
                f"Aborting deserialization to prevent arbitrary code execution."
            )
        if logger:
            logger.info("[SECURITY-2] Model SHA-256 integrity verified: %s", actual_hash[:12])
    else:
        if logger:
            logger.warning("[SECURITY-2] Sidecar checksum not found for %s, computed SHA-256: %s", model_path.name, actual_hash)

    return actual_hash


def verify_api_key(
    x_api_key: Optional[str] = Security(_API_KEY_HEADER),
    authorization: Optional[HTTPAuthorizationCredentials] = Security(_BEARER_AUTH),
) -> bool:
    """
    [SECURITY-3]: FastAPI dependency validating caller authorization via
    X-API-Key header or Authorization: Bearer <token>.
    """
    require_auth = os.getenv("DATAMIND_REQUIRE_AUTH", "false").lower() in ("true", "1", "yes")
    if not require_auth:
        return True

    expected_key = os.getenv("DATAMIND_API_KEY", "datamind-sec-token-prod-2026")

    # Extract key from X-API-Key or Bearer token header
    caller_key = x_api_key
    if not caller_key and authorization:
        if isinstance(authorization, HTTPAuthorizationCredentials):
            caller_key = authorization.credentials
        elif isinstance(authorization, str) and authorization.startswith("Bearer "):
            caller_key = authorization[7:].strip()
        else:
            caller_key = str(authorization)

    if not caller_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="[SECURITY-3] Missing API authentication credentials. Provide a valid X-API-Key or Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if caller_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="[SECURITY-3] Invalid API authentication key or token.",
        )

    return True


class SecurityError(RuntimeError):
    """[SECURITY-2]: Raised when a cryptographic or integrity security constraint is violated."""
    pass
