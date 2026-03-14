"""
HMAC QR Table Token — Story 3.3.

Token format:
  base64url(json_payload) + "." + hex(hmac_sha256(base64url(payload), secret))

Payload JSON:
  {"store_id": "<uuid>", "table_id": "<uuid>", "iat": <unix_ts>, "exp": <unix_ts>}

Redis replay guard:
  Key: qr:used:{token_hash}
  TTL: remaining seconds until token expiry

Error codes:
  INVALID_QR_TOKEN     — signature mismatch or malformed
  QR_TOKEN_EXPIRED     — valid but past expiry
  QR_TOKEN_ALREADY_USED — valid but already consumed
"""

import base64
import hashlib
import hmac
import json
import time as _time

import structlog

log = structlog.get_logger(__name__)

QR_TOKEN_TTL = 86400  # 24 hours in seconds
_REDIS_PREFIX = "qr:used:"


class QRTokenError(Exception):
    """Base for QR token validation errors."""

    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.code = code


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    # Add padding
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def generate_qr_token(store_id: str, table_id: str, secret: str, ttl: int = QR_TOKEN_TTL) -> str:
    """
    Generate a signed QR token for a table.

    Args:
        store_id: Store UUID string.
        table_id: Table UUID string.
        secret: HMAC-SHA256 signing secret (store-specific).
        ttl: Token lifetime in seconds (default 86400 = 24h).

    Returns:
        Token string: base64url(payload).hexhmac
    """
    now = int(_time.time())
    payload = {
        "store_id": store_id,
        "table_id": table_id,
        "iat": now,
        "exp": now + ttl,
    }
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    payload_b64 = _b64url_encode(payload_json.encode())

    sig = hmac.new(secret.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


def validate_qr_token(token: str, secret: str, redis_client) -> dict:
    """
    Validate a QR token and mark it as used in Redis.

    Args:
        token: Token string from query param.
        secret: HMAC-SHA256 signing secret.
        redis_client: Redis client for replay guard.

    Returns:
        dict with store_id, table_id, iat, exp.

    Raises:
        QRTokenError with code INVALID_QR_TOKEN, QR_TOKEN_EXPIRED,
        or QR_TOKEN_ALREADY_USED.
    """
    try:
        payload_b64, sig = token.rsplit(".", 1)
    except (ValueError, AttributeError):
        raise QRTokenError("Malformed token", code="INVALID_QR_TOKEN")

    # Verify HMAC
    expected_sig = hmac.new(
        secret.encode(), payload_b64.encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(sig, expected_sig):
        raise QRTokenError("Invalid token signature", code="INVALID_QR_TOKEN")

    # Decode payload
    try:
        payload_bytes = _b64url_decode(payload_b64)
        payload = json.loads(payload_bytes)
    except Exception:
        raise QRTokenError("Malformed token payload", code="INVALID_QR_TOKEN")

    # Check expiry
    now = int(_time.time())
    exp = payload.get("exp", 0)
    if now > exp:
        raise QRTokenError("Token has expired", code="QR_TOKEN_EXPIRED")

    # Replay guard — check Redis
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    redis_key = f"{_REDIS_PREFIX}{token_hash}"

    try:
        remaining_ttl = max(1, exp - now)
        # SET NX — only set if key does not exist
        already_used = not redis_client.set(redis_key, "1", nx=True, ex=remaining_ttl)
    except Exception as exc:
        # Redis unavailable — log and allow (fail open for availability)
        import sentry_sdk
        sentry_sdk.capture_exception(exc)
        log.warning("qr_redis_unavailable_replay_guard_skipped", error=str(exc))
        already_used = False

    if already_used:
        raise QRTokenError("Token already used", code="QR_TOKEN_ALREADY_USED")

    log.info(
        "qr_token_validated",
        store_id=payload.get("store_id"),
        table_id=payload.get("table_id"),
    )
    return payload
