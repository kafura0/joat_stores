"""
Tests for apps/payment/daraja.py — DarajaClient + get_daraja_client().

Mock strategy:
- Redis client: MagicMock() passed directly to DarajaClient constructor
- requests.get: patch("apps.payment.daraja.requests.get")
- sentry_sdk: patch("apps.payment.daraja.sentry_sdk.capture_exception")
- django_redis.get_redis_connection: patched for factory tests

Implementation: Story 2.1
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
import redis

from apps.payment.daraja import (
    TOKEN_TTL,
    DarajaClient,
    get_daraja_client,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_client(env="sandbox", mock_redis=None):
    """Build a DarajaClient with an injected mock Redis."""
    if mock_redis is None:
        mock_redis = MagicMock()
    return DarajaClient(
        env=env,
        consumer_key="test_key",
        consumer_secret="test_secret",
        redis_client=mock_redis,
        shortcode="174379",
        passkey="test_passkey",
    )


def daraja_response(token="test_access_token", status=200):
    """Build a mock requests.Response for a Daraja OAuth2 call."""
    resp = Mock()
    resp.status_code = status
    resp.json.return_value = {"access_token": token, "expires_in": "3599"}
    resp.text = ""
    return resp


# ---------------------------------------------------------------------------
# AC1 — token served from Redis cache
# ---------------------------------------------------------------------------


def test_ac1_token_served_from_cache():
    """AC1: cached token is returned — no HTTP call made."""
    mock_redis = MagicMock()
    mock_redis.get.return_value = b"cached_token_abc"
    client = make_client(mock_redis=mock_redis)

    with patch("apps.payment.daraja.requests.get") as mock_req:
        token = client.get_access_token()

    assert token == "cached_token_abc"
    mock_req.assert_not_called()


# ---------------------------------------------------------------------------
# AC2 — cache miss: lock acquired → fetch + cache write
# ---------------------------------------------------------------------------


def test_ac2_cache_miss_lock_acquired_fetches_and_caches():
    """AC2: cache miss + lock acquired → requests.get called, setex TTL 3500."""
    mock_redis = MagicMock()
    mock_redis.get.return_value = None  # cache miss
    mock_redis.set.return_value = True  # lock acquired

    client = make_client(mock_redis=mock_redis)

    with patch("apps.payment.daraja.requests.get") as mock_req:
        mock_req.return_value = daraja_response("new_token")
        token = client.get_access_token()

    assert token == "new_token"
    mock_req.assert_called_once()
    mock_redis.setex.assert_called_once_with(client._token_key, TOKEN_TTL, "new_token")
    mock_redis.delete.assert_called_once_with(client._lock_key)


# ---------------------------------------------------------------------------
# AC3 — cache miss: lock not acquired → poll cache, no extra HTTP call
# ---------------------------------------------------------------------------


def test_ac3_lock_not_acquired_polls_cache_and_returns():
    """AC3: lock not acquired → polls cache, returns token once available."""
    mock_redis = MagicMock()
    # get() calls: initial miss, first poll miss, second poll hit
    mock_redis.get.side_effect = [
        None,
        None,
        b"token_from_other_worker",
    ]
    mock_redis.set.return_value = None  # lock not acquired

    client = make_client(mock_redis=mock_redis)

    with (
        patch("apps.payment.daraja.requests.get") as mock_req,
        patch("apps.payment.daraja.time.sleep"),
    ):
        token = client.get_access_token()

    assert token == "token_from_other_worker"
    mock_req.assert_not_called()


def test_lock_wait_timeout_falls_through_to_direct_fetch():
    """Edge case: fetcher never populates cache within LOCK_MAX_WAIT."""
    mock_redis = MagicMock()
    # All get() calls return None (token never appears)
    mock_redis.get.return_value = None
    mock_redis.set.return_value = None  # lock not acquired

    client = make_client(mock_redis=mock_redis)

    with (
        patch("apps.payment.daraja.requests.get") as mock_req,
        patch("apps.payment.daraja.time.sleep"),
        patch("apps.payment.daraja.LOCK_MAX_WAIT", 0.0),
    ):
        mock_req.return_value = daraja_response("direct_fetch_token")
        token = client.get_access_token()

    assert token == "direct_fetch_token"
    mock_req.assert_called_once()
    # No caching during lock-wait timeout fallthrough
    mock_redis.setex.assert_not_called()


# ---------------------------------------------------------------------------
# AC4 — sandbox / production URL switching
# ---------------------------------------------------------------------------


def test_ac4_sandbox_url():
    """AC4: sandbox env → URL targets sandbox.safaricom.co.ke."""
    client = make_client(env="sandbox")
    assert "sandbox.safaricom.co.ke" in client._build_token_url()


def test_ac4_production_url():
    """AC4: production env → URL targets api.safaricom.co.ke."""
    client = make_client(env="production")
    assert "api.safaricom.co.ke" in client._build_token_url()


def test_ac4_url_includes_grant_type():
    """AC4: URL includes correct OAuth2 grant_type parameter."""
    client = make_client(env="sandbox")
    assert "grant_type=client_credentials" in client._build_token_url()


# ---------------------------------------------------------------------------
# AC5 — credentials via constructor, correct Basic Auth header
# ---------------------------------------------------------------------------


def test_ac5_credentials_passed_via_constructor():
    """AC5: consumer_key/secret from constructor → correct Basic Auth."""
    mock_redis = MagicMock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True

    client = DarajaClient(
        env="sandbox",
        consumer_key="my_key",
        consumer_secret="my_secret",
        redis_client=mock_redis,
        shortcode="174379",
        passkey="test_passkey",
    )

    with patch("apps.payment.daraja.requests.get") as mock_req:
        mock_req.return_value = daraja_response()
        client.get_access_token()

    assert mock_req.call_args.kwargs["auth"] == ("my_key", "my_secret")


def test_ac5_timeout_is_five_seconds():
    """AC5: HTTP request uses 5-second timeout."""
    mock_redis = MagicMock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    client = make_client(mock_redis=mock_redis)

    with patch("apps.payment.daraja.requests.get") as mock_req:
        mock_req.return_value = daraja_response()
        client.get_access_token()

    assert mock_req.call_args.kwargs["timeout"] == 5


# ---------------------------------------------------------------------------
# AC6 — Redis unavailable fallback
# ---------------------------------------------------------------------------


def test_ac6_redis_unavailable_fallback_fetches_token():
    """AC6: ConnectionError → sentry captured, direct fetch, no setex."""
    mock_redis = MagicMock()
    mock_redis.get.side_effect = redis.exceptions.ConnectionError("refused")
    client = make_client(mock_redis=mock_redis)

    with (
        patch("apps.payment.daraja.requests.get") as mock_req,
        patch("apps.payment.daraja.sentry_sdk.capture_exception") as mock_capture,
    ):
        mock_req.return_value = daraja_response("fallback_token")
        token = client.get_access_token()

    assert token == "fallback_token"
    mock_capture.assert_called_once()
    mock_redis.setex.assert_not_called()
    mock_req.assert_called_once()


def test_ac6_redis_error_also_triggers_fallback():
    """AC6: generic RedisError also triggers fallback path."""
    mock_redis = MagicMock()
    mock_redis.get.side_effect = redis.exceptions.RedisError("generic")
    client = make_client(mock_redis=mock_redis)

    with (
        patch("apps.payment.daraja.requests.get") as mock_req,
        patch("apps.payment.daraja.sentry_sdk.capture_exception") as mock_capture,
    ):
        mock_req.return_value = daraja_response("fallback_token_2")
        token = client.get_access_token()

    assert token == "fallback_token_2"
    mock_capture.assert_called_once()
    mock_redis.setex.assert_not_called()


# ---------------------------------------------------------------------------
# _fetch_token_from_daraja — non-200 and malformed response
# ---------------------------------------------------------------------------


def test_fetch_raises_on_non_200_daraja_response():
    """non-200 Daraja response raises (via raise_for_status)."""
    mock_redis = MagicMock()
    client = make_client(mock_redis=mock_redis)

    error_resp = Mock()
    error_resp.status_code = 401
    error_resp.text = "Unauthorized"
    error_resp.raise_for_status.side_effect = Exception("HTTP 401")

    with patch("apps.payment.daraja.requests.get") as mock_req:
        mock_req.return_value = error_resp
        with pytest.raises(Exception, match="HTTP 401"):
            client._fetch_token_from_daraja()


def test_fetch_raises_on_missing_access_token_key():
    """M1: response JSON without 'access_token' key raises ValueError."""
    mock_redis = MagicMock()
    client = make_client(mock_redis=mock_redis)

    bad_resp = Mock()
    bad_resp.status_code = 200
    bad_resp.json.return_value = {"errorCode": "404.001.03", "errorMessage": "Bad"}
    bad_resp.text = ""

    with patch("apps.payment.daraja.requests.get") as mock_req:
        mock_req.return_value = bad_resp
        with pytest.raises(ValueError, match="access_token"):
            client._fetch_token_from_daraja()


# ---------------------------------------------------------------------------
# DarajaClient.__init__ — env validation
# ---------------------------------------------------------------------------


def test_init_raises_on_invalid_env():
    """M2: DarajaClient raises ValueError for unknown env."""
    mock_redis = MagicMock()
    with pytest.raises(ValueError, match="env must be one of"):
        DarajaClient(
            env="staging",
            consumer_key="key",
            consumer_secret="secret",
            redis_client=mock_redis,
            shortcode="174379",
            passkey="test_passkey",
        )


# ---------------------------------------------------------------------------
# get_daraja_client() factory — ImproperlyConfigured for missing settings
# ---------------------------------------------------------------------------


def test_get_daraja_client_raises_when_credentials_missing():
    """get_daraja_client() raises ImproperlyConfigured with empty creds."""
    from django.core.exceptions import ImproperlyConfigured
    from django.test import override_settings

    with override_settings(
        MPESA_ENV="sandbox",
        MPESA_CONSUMER_KEY="",
        MPESA_CONSUMER_SECRET="",
        MPESA_SHORTCODE="",
        MPESA_PASSKEY="",
    ):
        with pytest.raises(ImproperlyConfigured, match="Missing required"):
            get_daraja_client()


def test_get_daraja_client_raises_on_invalid_env():
    """get_daraja_client() raises ImproperlyConfigured for unknown MPESA_ENV."""
    from django.core.exceptions import ImproperlyConfigured
    from django.test import override_settings

    with (
        override_settings(
            MPESA_ENV="staging",
            MPESA_CONSUMER_KEY="key",
            MPESA_CONSUMER_SECRET="secret",
            MPESA_SHORTCODE="174379",
            MPESA_PASSKEY="test_passkey",
        ),
        patch("django_redis.get_redis_connection"),
    ):
        with pytest.raises(ImproperlyConfigured, match="MPESA_ENV must be"):
            get_daraja_client()


def test_get_daraja_client_returns_daraja_client():
    """get_daraja_client() happy path returns a configured DarajaClient."""
    from django.test import override_settings

    with (
        override_settings(
            MPESA_ENV="sandbox",
            MPESA_CONSUMER_KEY="test_key",
            MPESA_CONSUMER_SECRET="test_secret",
            MPESA_SHORTCODE="174379",
            MPESA_PASSKEY="test_passkey",
        ),
        patch("django_redis.get_redis_connection") as mock_conn,
    ):
        mock_conn.return_value = MagicMock()
        client = get_daraja_client()

    assert isinstance(client, DarajaClient)
    assert client._env == "sandbox"
    assert client._consumer_key == "test_key"
    assert client._shortcode == "174379"
