"""Daraja (M-Pesa) API client with OAuth2 token caching.

DarajaClient caches the Daraja OAuth2 access token in Redis to avoid
hitting the token endpoint on every STK Push request.

Caching strategy:
- Redis key: daraja:access_token:{env}, TTL 3500s
- Concurrent-worker safety: SET NX lock (daraja:token_lock:{env})
- Redis-unavailable fallback: direct fetch + Sentry capture

Factory:
    get_daraja_client() — builds DarajaClient from Django settings

Implementation: Story 2.1 (token cache), Story 2.2 (STK Push)
"""

import base64
import time
from datetime import datetime, timezone

from django.core.exceptions import ImproperlyConfigured

import redis as redis_lib
import requests
import sentry_sdk
import structlog

from apps.payment.exceptions import (
    ReversalError,
    StkPushError,
    TransactionStatusQueryError,
)

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# URL map per environment
# ---------------------------------------------------------------------------
DARAJA_URLS = {
    "sandbox": "https://sandbox.safaricom.co.ke",
    "production": "https://api.safaricom.co.ke",
}

# ---------------------------------------------------------------------------
# Redis key templates and timing constants
# ---------------------------------------------------------------------------
TOKEN_CACHE_KEY = "daraja:access_token:{env}"
TOKEN_LOCK_KEY = "daraja:token_lock:{env}"

TOKEN_TTL = 3500  # seconds (Daraja tokens expire at 3599s; buffer of ~99s)
LOCK_TTL = 15  # seconds — auto-expire lock if fetcher crashes
LOCK_WAIT_INTERVAL = 0.2  # seconds — poll interval while waiting for lock
LOCK_MAX_WAIT = 10  # seconds — give up waiting, fetch directly

# ---------------------------------------------------------------------------
# API paths
# ---------------------------------------------------------------------------
MPESA_STK_PUSH_PATH = "/mpesa/stkpush/v1/processrequest"
MPESA_REVERSAL_PATH = "/mpesa/reversal/v1/request"
MPESA_STK_QUERY_PATH = "/mpesa/stkpushquery/v1/query"
MPESA_C2B_REGISTER_PATH = "/mpesa/c2b/v1/registerurl"


class DarajaClient:
    """Daraja OAuth2 client with Redis-cached access tokens and STK Push.

    All dependencies are injected — no env reads inside __init__.
    """

    def __init__(
        self,
        env: str,
        consumer_key: str,
        consumer_secret: str,
        redis_client,
        shortcode: str,
        passkey: str,
        initiator_name: str = "",
        security_credential: str = "",
    ) -> None:
        if env not in DARAJA_URLS:
            raise ValueError(
                f"env must be one of {list(DARAJA_URLS.keys())}, got {env!r}"
            )
        self._env = env
        self._consumer_key = consumer_key
        self._consumer_secret = consumer_secret
        self._redis = redis_client
        self._shortcode = shortcode
        self._passkey = passkey
        self._initiator_name = initiator_name
        self._security_credential = security_credential
        self._base_url = DARAJA_URLS[env]
        self._token_key = TOKEN_CACHE_KEY.format(env=env)
        self._lock_key = TOKEN_LOCK_KEY.format(env=env)

    # ------------------------------------------------------------------
    # OAuth2 token management (Story 2.1)
    # ------------------------------------------------------------------

    def get_access_token(self) -> str:
        """Return a valid Daraja OAuth2 access token.

        Serves from Redis when cached. On cache miss: one Celery worker
        fetches (via SET NX lock) while others poll. Falls back to a
        direct fetch if Redis is unavailable.
        """
        try:
            return self._get_token_from_cache_with_lock()
        except (
            redis_lib.exceptions.ConnectionError,
            redis_lib.exceptions.RedisError,
        ) as exc:
            sentry_sdk.capture_exception(exc)
            log.warning("redis_unavailable_daraja_token_fallback")
            return self._fetch_token_from_daraja()

    def _get_token_from_cache_with_lock(self) -> str:
        # Step 1: fast path — token already in cache
        cached = self._redis.get(self._token_key)
        if cached:
            log.debug("daraja_token_cache_hit")
            return cached.decode()

        # Step 2: try to become the fetcher via SET NX lock
        acquired = self._redis.set(self._lock_key, "1", nx=True, ex=LOCK_TTL)
        if acquired:
            try:
                token = self._fetch_token_from_daraja()
                self._redis.setex(self._token_key, TOKEN_TTL, token)
                log.info("daraja_token_fetched_and_cached", ttl=TOKEN_TTL)
                return token
            finally:
                self._redis.delete(self._lock_key)

        # Step 3: wait for the fetcher to populate the cache
        waited = 0.0
        while waited < LOCK_MAX_WAIT:
            time.sleep(LOCK_WAIT_INTERVAL)
            waited += LOCK_WAIT_INTERVAL
            cached = self._redis.get(self._token_key)
            if cached:
                log.debug(
                    "daraja_token_received_after_lock_wait",
                    waited=waited,
                )
                return cached.decode()

        # Fetcher took too long — fetch directly (rare edge case)
        log.warning("daraja_lock_wait_timeout_direct_fetch", waited=waited)
        return self._fetch_token_from_daraja()

    def _fetch_token_from_daraja(self) -> str:
        """Fetch a fresh OAuth2 token from Daraja. Raises on non-200."""
        url = self._build_token_url()
        log.debug("daraja_token_fetch_start", url=url)
        response = requests.get(
            url,
            auth=(self._consumer_key, self._consumer_secret),
            timeout=5,
        )
        if response.status_code != 200:
            log.error(
                "daraja_token_fetch_failed",
                status=response.status_code,
                body=response.text[:200],
            )
            response.raise_for_status()
        data = response.json()
        token = data.get("access_token")
        if not token:
            log.error(
                "daraja_token_fetch_unexpected_response",
                keys=list(data.keys()),
            )
            raise ValueError(
                f"Daraja OAuth2 response missing 'access_token'. "
                f"Keys received: {list(data.keys())}"
            )
        log.info("daraja_token_fetch_success")
        return token

    def _build_token_url(self) -> str:
        return f"{self._base_url}/oauth/v1/generate?grant_type=client_credentials"

    # ------------------------------------------------------------------
    # STK Push (Story 2.2)
    # ------------------------------------------------------------------

    def initiate_stk_push(
        self,
        phone: str,
        amount: str,
        reference: str,
        callback_url: str,
    ) -> dict:
        """Initiate an STK Push and return the Daraja response dict.

        Args:
            phone: E.164 phone number (e.g. "+254712345678"). Leading '+' is
                   stripped before building the Daraja payload.
            amount: Integer string (e.g. "100"). Decimals are stripped.
            reference: Order/tab/subscription reference (max 12 chars recommended).
            callback_url: Full URL where Daraja will POST the webhook result.

        Returns:
            dict with at least CheckoutRequestID, MerchantRequestID,
            ResponseCode, CustomerMessage.

        Raises:
            StkPushError: on non-200 HTTP, non-"0" ResponseCode, or network error.
        """
        token = self.get_access_token()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        password = self._build_stk_password(timestamp)

        # Daraja expects phone without leading '+'
        daraja_phone = phone.lstrip("+")
        daraja_amount = str(int(amount))

        payload = {
            "BusinessShortCode": self._shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": daraja_amount,
            "PartyA": daraja_phone,
            "PartyB": self._shortcode,
            "PhoneNumber": daraja_phone,
            "CallBackURL": callback_url,
            "AccountReference": reference[:12],
            "TransactionDesc": f"Payment for {reference}"[:13],
        }

        try:
            response = requests.post(
                f"{self._base_url}{MPESA_STK_PUSH_PATH}",
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
        except requests.exceptions.RequestException as exc:
            log.error("stk_push_network_error", reference=reference, error=str(exc))
            raise StkPushError("Network error during STK Push") from exc

        if response.status_code != 200:
            log.error(
                "stk_push_http_error",
                status=response.status_code,
                body=response.text[:200],
            )
            raise StkPushError(f"HTTP {response.status_code}")

        response_data = response.json()
        if response_data.get("ResponseCode") != "0":
            log.error(
                "stk_push_daraja_error",
                response_code=response_data.get("ResponseCode"),
                error_message=response_data.get("errorMessage", ""),
            )
            raise StkPushError(
                response_data.get("errorMessage", "Unknown Daraja error")
            )

        log.info(
            "stk_push_initiated",
            checkout_request_id=response_data.get("CheckoutRequestID"),
            reference=reference,
        )
        return response_data

    def _build_stk_password(self, timestamp: str) -> str:
        """Generate the Lipa Na M-Pesa Online password.

        base64(BusinessShortCode + Passkey + Timestamp)
        """
        raw = f"{self._shortcode}{self._passkey}{timestamp}"
        return base64.b64encode(raw.encode()).decode()

    # ------------------------------------------------------------------
    # Reversal API (Story 2.5)
    # ------------------------------------------------------------------

    def initiate_reversal(
        self,
        transaction_id: str,
        amount: str,
        reason: str,
    ) -> dict:
        """Initiate an M-Pesa reversal via the Daraja Reversal API.

        Args:
            transaction_id: The MpesaReceiptNumber of the confirmed transaction.
            amount: Integer string e.g. "100".
            reason: Human-readable reversal reason (stored as Remarks).

        Returns:
            Daraja response dict.

        Raises:
            ReversalError: on non-200 HTTP or ResultCode != 0.
        """
        token = self.get_access_token()
        callback_base = self._base_url  # fallback; real callback from settings

        payload = {
            "Initiator": self._initiator_name,
            "SecurityCredential": self._security_credential,
            "CommandID": "TransactionReversal",
            "TransactionID": transaction_id,
            "Amount": amount,
            "ReceiverParty": self._shortcode,
            "RecieverIdentifierType": "11",
            "ResultURL": f"{callback_base}/reversal-result/",
            "QueueTimeOutURL": f"{callback_base}/reversal-timeout/",
            "Remarks": reason,
            "Occasion": "",
        }

        try:
            response = requests.post(
                f"{self._base_url}{MPESA_REVERSAL_PATH}",
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
        except requests.exceptions.RequestException as exc:
            log.error(
                "reversal_network_error",
                transaction_id=transaction_id,
                error=str(exc),
            )
            raise ReversalError("Network error during reversal") from exc

        if response.status_code != 200:
            log.error(
                "reversal_http_error",
                status=response.status_code,
                body=response.text[:200],
            )
            raise ReversalError(f"HTTP {response.status_code}")

        response_data = response.json()
        result = response_data.get("Result", {})
        if int(result.get("ResultCode", 1)) != 0:
            log.error(
                "reversal_daraja_error",
                result_code=result.get("ResultCode"),
                result_desc=result.get("ResultDesc", ""),
            )
            raise ReversalError(
                result.get("ResultDesc", "Daraja reversal rejected")
            )

        log.info(
            "reversal_initiated",
            transaction_id=transaction_id,
        )
        return response_data

    # ------------------------------------------------------------------
    # Transaction Status Query API (Story 2.5)
    # ------------------------------------------------------------------

    def query_transaction_status(self, checkout_request_id: str) -> dict:
        """Query Daraja for the current status of an STK Push.

        Args:
            checkout_request_id: The CheckoutRequestID from the original push.

        Returns:
            dict with at least ResultCode (as int) and ResultDesc.

        Raises:
            TransactionStatusQueryError: on non-200 HTTP or API error.
        """
        token = self.get_access_token()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        password = self._build_stk_password(timestamp)

        payload = {
            "BusinessShortCode": self._shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id,
        }

        try:
            response = requests.post(
                f"{self._base_url}{MPESA_STK_QUERY_PATH}",
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
        except requests.exceptions.RequestException as exc:
            log.error(
                "stk_query_network_error",
                checkout_request_id=checkout_request_id,
                error=str(exc),
            )
            raise TransactionStatusQueryError(
                "Network error during status query"
            ) from exc

        if response.status_code != 200:
            log.error(
                "stk_query_http_error",
                status=response.status_code,
                body=response.text[:200],
            )
            raise TransactionStatusQueryError(f"HTTP {response.status_code}")

        response_data = response.json()
        if response_data.get("ResponseCode") != "0":
            log.error(
                "stk_query_daraja_error",
                response_code=response_data.get("ResponseCode"),
            )
            raise TransactionStatusQueryError(
                response_data.get("ResponseDescription", "Query rejected")
            )

        return {
            "ResultCode": int(response_data.get("ResultCode", "999")),
            "ResultDesc": response_data.get("ResultDesc", ""),
        }

    # ------------------------------------------------------------------
    # C2B Register URL (till number / paybill)
    # ------------------------------------------------------------------

    def register_c2b_url(self, confirmation_url: str, validation_url: str) -> dict:
        """Register C2B callback URLs with Safaricom.

        Once registered, all customer-initiated payments to the till/paybill
        number will trigger POST to confirmation_url.

        Args:
            confirmation_url: Full URL for payment confirmation callbacks.
            validation_url: Full URL for payment validation (optional pre-check).

        Returns:
            Daraja response dict with ResponseCode, ResponseDescription.
        """
        token = self.get_access_token()

        payload = {
            "ShortCode": self._shortcode,
            "ResponseType": "Completed",
            "ConfirmationURL": confirmation_url,
            "ValidationURL": validation_url,
        }

        try:
            response = requests.post(
                f"{self._base_url}{MPESA_C2B_REGISTER_PATH}",
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
        except requests.exceptions.RequestException as exc:
            log.error("c2b_register_network_error", error=str(exc))
            raise StkPushError("Network error during C2B Register URL") from exc

        if response.status_code != 200:
            log.error(
                "c2b_register_http_error",
                status=response.status_code,
                body=response.text[:200],
            )
            raise StkPushError(f"HTTP {response.status_code}")

        response_data = response.json()
        log.info("c2b_register_success", response=response_data)
        return response_data


def get_daraja_client() -> DarajaClient:
    """Construct DarajaClient from Django settings / env vars.

    Raises ImproperlyConfigured if any required setting is absent or empty.
    """
    from django.conf import settings

    from django_redis import get_redis_connection

    mpesa_env = getattr(settings, "MPESA_ENV", "")
    consumer_key = getattr(settings, "MPESA_CONSUMER_KEY", "")
    consumer_secret = getattr(settings, "MPESA_CONSUMER_SECRET", "")
    mpesa_shortcode = getattr(settings, "MPESA_SHORTCODE", "")
    mpesa_passkey = getattr(settings, "MPESA_PASSKEY", "")
    initiator_name = getattr(settings, "MPESA_INITIATOR_NAME", "")
    security_credential = getattr(settings, "MPESA_SECURITY_CREDENTIAL", "")

    missing = [
        name
        for name, val in [
            ("MPESA_ENV", mpesa_env),
            ("MPESA_CONSUMER_KEY", consumer_key),
            ("MPESA_CONSUMER_SECRET", consumer_secret),
            ("MPESA_SHORTCODE", mpesa_shortcode),
            ("MPESA_PASSKEY", mpesa_passkey),
        ]
        if not val
    ]
    if missing:
        raise ImproperlyConfigured(
            f"Missing required M-Pesa settings: {', '.join(missing)}"
        )

    if mpesa_env not in DARAJA_URLS:
        raise ImproperlyConfigured(
            f"MPESA_ENV must be one of {list(DARAJA_URLS.keys())}, "
            f"got {mpesa_env!r}"
        )

    redis_client = get_redis_connection("default")
    return DarajaClient(
        env=mpesa_env,
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        redis_client=redis_client,
        shortcode=mpesa_shortcode,
        passkey=mpesa_passkey,
        initiator_name=initiator_name,
        security_credential=security_credential,
    )
