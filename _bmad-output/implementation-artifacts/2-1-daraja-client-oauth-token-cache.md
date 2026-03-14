# Story 2.1: Daraja Client + OAuth Token Cache

Status: done

---

## Story

As a payment system,
I want the Daraja OAuth2 access token to be cached in Redis rather than fetched per transaction,
So that every STK Push is fast and we never hit Daraja rate limits on token endpoints.

---

## Acceptance Criteria

**AC1 — Token served from Redis cache**

Given the Daraja client needs an access token
When the token exists in Redis at key `daraja:access_token:{env}` with a valid TTL
Then the cached token is returned — no call to Daraja OAuth2 endpoint is made

**AC2 — Cache miss triggers fetch + cache write**

Given the Redis key is absent or expired
When `get_access_token()` is called
Then a new token is fetched from Daraja OAuth2
And stored in Redis at `daraja:access_token:{env}` with TTL 3500s

**AC3 — Concurrent worker safety (SET NX lock)**

Given the Daraja client is called simultaneously by multiple Celery workers
When the Redis token key is absent
Then only one worker fetches a new token (via Redis SET NX lock)
And the others wait then read the token from cache once it's populated

**AC4 — Sandbox / production URL switching**

Given `MPESA_ENV=sandbox` is set
When the client initializes
Then all API calls target `sandbox.safaricom.co.ke` endpoints
And switching to `MPESA_ENV=production` targets `api.safaricom.co.ke` with no code changes

**AC5 — Credentials from environment variables only**

Given Daraja API credentials are needed
When the client loads them
Then `MPESA_CONSUMER_KEY` and `MPESA_CONSUMER_SECRET` are read from environment variables
And they are never hardcoded in source code

**AC6 — Redis unavailable fallback**

Given Redis is unavailable (ConnectionError)
When the token fetch is attempted
Then the client falls back to a single direct token fetch from Daraja with a 5-second timeout
And `sentry_sdk.capture_exception()` is called immediately — never a silent failure
And the fallback token is NOT written to Redis (no cache write during outage)

---

## Tasks / Subtasks

- [x] **Task 1: Add `requests` to `backend/requirements/base.txt`** (AC: 2, 6)
  - [x] Add `requests==2.*` below the `# Utilities` section in `base.txt`
  - [x] No other requirements file changes needed — `requests` is a runtime dependency

- [x] **Task 2: Create `apps/payment/daraja.py` — DarajaClient** (AC: 1, 2, 3, 4, 5, 6)
  - [x] Define module-level constants:
    - `DARAJA_URLS`: dict mapping `env` → base URL (`sandbox`: `https://sandbox.safaricom.co.ke`, `production`: `https://api.safaricom.co.ke`)
    - `TOKEN_CACHE_KEY`: `"daraja:access_token:{env}"` template
    - `TOKEN_LOCK_KEY`: `"daraja:token_lock:{env}"` template
    - `TOKEN_TTL`: `3500` (seconds — Daraja tokens expire in 3599s)
    - `LOCK_TTL`: `15` (seconds — max time to hold the fetch lock)
    - `LOCK_WAIT_INTERVAL`: `0.2` (seconds — poll interval when waiting for lock)
    - `LOCK_MAX_WAIT`: `10` (seconds — give up after this long)
  - [x] Implement `DarajaClient` class:
    - [x] `__init__(self, env: str, consumer_key: str, consumer_secret: str, redis_client)` — all injected, no env reads inside `__init__`
    - [x] `get_access_token(self) -> str` — main method (see logic below)
    - [x] `_fetch_token_from_daraja(self) -> str` — HTTP Basic Auth GET to OAuth2 endpoint, 5s timeout, raises on non-200
    - [x] `_build_token_url(self) -> str` — returns `{base_url}/oauth/v1/generate?grant_type=client_credentials`
  - [x] `get_access_token()` logic:
    - [x] Step 1: `redis.get(TOKEN_CACHE_KEY)` — if hit, return decoded token string
    - [x] Step 2: Attempt `redis.set(TOKEN_LOCK_KEY, "1", nx=True, ex=LOCK_TTL)` — try to be the fetcher
    - [x] Step 3a (lock acquired): call `_fetch_token_from_daraja()`, then `redis.setex(TOKEN_CACHE_KEY, TOKEN_TTL, token)`, release lock via `redis.delete(TOKEN_LOCK_KEY)`, return token
    - [x] Step 3b (lock not acquired): poll `redis.get(TOKEN_CACHE_KEY)` every `LOCK_WAIT_INTERVAL` seconds up to `LOCK_MAX_WAIT`; if token appears, return it; if timeout expires, fall through to direct fetch
    - [x] Step 4 (Redis unavailable — `redis.exceptions.ConnectionError` or `redis.exceptions.RedisError`): call `_fetch_token_from_daraja()` with 5s timeout, call `sentry_sdk.capture_exception(exc)`, return token WITHOUT caching
  - [x] Use `structlog.get_logger(__name__)` for all log statements — never `print()` or bare `logging`

- [x] **Task 3: Add `get_daraja_client()` factory function** (AC: 4, 5)
  - [x] In `apps/payment/daraja.py`, add module-level factory:
    ```python
    def get_daraja_client() -> DarajaClient:
        """Construct DarajaClient from Django settings / env vars."""
    ```
  - [x] Reads `MPESA_ENV`, `MPESA_CONSUMER_KEY`, `MPESA_CONSUMER_SECRET` from `django.conf.settings`
  - [x] Gets Redis client via `django_redis.get_redis_connection("default")` — uses the project's configured Redis
  - [x] Raises `ImproperlyConfigured` if any required setting is missing

- [x] **Task 4: Add env vars to `.envs/.local/.django`** (AC: 4, 5)
  - [x] Add sandbox placeholder values (safe for local dev / CI):
    ```
    MPESA_ENV=sandbox
    MPESA_CONSUMER_KEY=sandbox_consumer_key_placeholder
    MPESA_CONSUMER_SECRET=sandbox_consumer_secret_placeholder
    ```
  - [x] Add corresponding entries to Django settings (`config/settings/base.py`): `MPESA_ENV`, `MPESA_CONSUMER_KEY`, `MPESA_CONSUMER_SECRET` read via `env()`

- [x] **Task 5: Write tests in `apps/payment/tests/test_daraja.py`** (AC: 1, 2, 3, 4, 5, 6)
  - [x] Use `unittest.mock.patch` — mock `requests.get` and Redis client
  - [x] AC1: token in cache → `redis.get` returns token, no `requests.get` call
  - [x] AC2: cache miss + lock acquired → `requests.get` called once, `redis.setex` called with TTL 3500
  - [x] AC3: cache miss + lock not acquired → polls cache, returns token once it appears (no extra `requests.get`)
  - [x] AC4: `MPESA_ENV=sandbox` → URL contains `sandbox.safaricom.co.ke`; `MPESA_ENV=production` → `api.safaricom.co.ke`
  - [x] AC5: credentials passed via constructor (not hardcoded); assert `requests.get` receives correct Basic Auth header
  - [x] AC6: `redis.get` raises `ConnectionError` → `_fetch_token_from_daraja` called, `sentry_sdk.capture_exception` called, `redis.setex` NOT called
  - [x] Test `_fetch_token_from_daraja` raises on non-200 Daraja response
  - [x] Test `get_daraja_client()` raises `ImproperlyConfigured` when env vars are missing

### Review Follow-ups (AI)

- [ ] [AI-Review][LOW] No test for `requests` network exceptions (Timeout, ConnectionError from requests lib) in `_fetch_token_from_daraja` — only non-200 HTTP is covered (`test_daraja.py`)
- [ ] [AI-Review][LOW] `test_get_daraja_client_raises_when_credentials_missing` only exercises missing key/secret — add a case where `MPESA_ENV` itself is empty (`test_daraja.py`)
- [ ] [AI-Review][LOW] `log.info("daraja_token_fetch_start", url=url)` fires on every token refresh (~58 min cycle) — the URL is constant for sandbox/production; consider `log.debug` to reduce production log noise (`daraja.py:123`)

---

## Dev Notes

### Daraja OAuth2 API

```
Endpoint (sandbox): GET https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials
Endpoint (prod):    GET https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials

Auth: HTTP Basic Auth — base64(consumer_key:consumer_secret)
      requests handles this automatically with `auth=(consumer_key, consumer_secret)`

Response (200):
{
  "access_token": "Uyy0mUsVYhFVc2...",
  "expires_in": "3599"
}

Note: TTL is 3599s from Daraja. We cache for 3500s to avoid serving a token
that's about to expire. Never cache for the full 3599s.
```

### Redis Key Design

```
daraja:access_token:sandbox     ← token value, TTL 3500s
daraja:access_token:production  ← separate key per environment
daraja:token_lock:sandbox       ← SET NX lock, TTL 15s auto-expire
```

### Concurrent Worker Safety Pattern

```python
# Simplified pseudocode
def get_access_token(self):
    # 1. Cache hit (fast path)
    cached = self.redis.get(self._token_key)
    if cached:
        return cached.decode()

    # 2. Try to be the fetcher
    acquired = self.redis.set(self._lock_key, "1", nx=True, ex=LOCK_TTL)

    if acquired:
        try:
            token = self._fetch_token_from_daraja()
            self.redis.setex(self._token_key, TOKEN_TTL, token)
            return token
        finally:
            self.redis.delete(self._lock_key)
    else:
        # 3. Wait for the fetcher to populate cache
        waited = 0
        while waited < LOCK_MAX_WAIT:
            time.sleep(LOCK_WAIT_INTERVAL)
            waited += LOCK_WAIT_INTERVAL
            cached = self.redis.get(self._token_key)
            if cached:
                return cached.decode()
        # Fetcher took too long — fetch directly (rare edge case)
        return self._fetch_token_from_daraja()
```

### Redis Unavailable Fallback

```python
try:
    return self.get_access_token_from_cache_with_lock()
except (redis.exceptions.ConnectionError, redis.exceptions.RedisError) as exc:
    import sentry_sdk
    sentry_sdk.capture_exception(exc)
    log.warning("redis_unavailable_daraja_token_fallback")
    return self._fetch_token_from_daraja()
    # NOTE: no redis.setex here — do not attempt Redis during outage
```

### Django Settings Additions

```python
# config/settings/base.py
MPESA_ENV = env("MPESA_ENV", default="sandbox")  # "sandbox" | "production"
MPESA_CONSUMER_KEY = env("MPESA_CONSUMER_KEY", default="")
MPESA_CONSUMER_SECRET = env("MPESA_CONSUMER_SECRET", default="")
```

### `django_redis` vs raw `redis-py`

The project uses `django-redis` for the cache backend (configured in cookiecutter-django). Use `django_redis.get_redis_connection("default")` to get the raw Redis client — this ensures the client uses the same connection pool as the rest of the app. Do NOT create a new `redis.Redis()` instance directly.

Check if `django-redis` is in requirements — if not, add it. It's typically included by cookiecutter-django.

### Previous Story Learnings (Story 2.0)

- Implementation of pure utilities belongs in `core/` not `apps/`. However, `DarajaClient` is payment-specific with Django dependencies — it belongs in `apps/payment/daraja.py` as per architecture.
- `core/utils.py` import should always be `core.*` never `apps.*` — enforced by Story 2.0 review.
- flake8 (`--max-line-length=120`) + black + isort must all pass before marking tasks complete.
- All tests: `python -m pytest apps/payment/tests/test_daraja.py -v`

### Architecture Constraints

- `structlog.get_logger(__name__)` — never `print()` or `logging.info()`
- `requests` library for HTTP — add to `base.txt` (not currently listed)
- Credentials via `django.conf.settings` — never `os.environ.get()` directly in app code
- `ImproperlyConfigured` from `django.core.exceptions` for missing config
- `DarajaClient` is NOT a Django model — plain Python class, no `TenantModel`
- Tests use `unittest.mock.patch`, not `pytest-mock` (not in requirements)
- `@pytest.mark.django_db` needed for `get_daraja_client()` factory test (reads Django settings)

### Files to Create / Modify

| File | Action |
|---|---|
| `backend/requirements/base.txt` | **MODIFY** — add `requests==2.*` |
| `backend/apps/payment/daraja.py` | **CREATE** — DarajaClient + get_daraja_client() |
| `backend/apps/payment/tests/test_daraja.py` | **CREATE** — full mock-based test suite |
| `backend/.envs/.local/.django` | **MODIFY** — add MPESA_* sandbox vars |
| `backend/config/settings/base.py` | **MODIFY** — add MPESA_* settings |

### References

- Epic 2 Story 2.1 spec: `_bmad-output/planning-artifacts/epics.md` line 802
- Architecture — Daraja client location: `_bmad-output/planning-artifacts/architecture.md` line 656
- Architecture — Redis usage: `_bmad-output/planning-artifacts/architecture.md` line 888
- Architecture — structlog enforcement: `_bmad-output/planning-artifacts/architecture.md` line 551
- Architecture — env var naming: `_bmad-output/planning-artifacts/architecture.md` line 340

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- `TypeError: 'str' object is not callable` in daraja tests: structlog's processor list in `config/settings/base.py` had `"core.audit.scrub_pii"` as a string literal instead of the imported callable. Fixed by adding `from core.audit import scrub_pii` and replacing the string with `scrub_pii`. Pre-existing bug first exposed by daraja.py's `log.*()` calls.
- `@pytest.mark.django_db` not needed for factory tests: `get_daraja_client()` reads Django settings only (no ORM queries). Removed the decorator; `override_settings()` works without DB access.

### Completion Notes List

- `apps/payment/daraja.py`: `DarajaClient` class (injected constructor) + `get_daraja_client()` factory. Redis SET NX lock for concurrent workers, TTL 3500s token cache, Redis-unavailable fallback via Sentry. `structlog` for all logging, `sentry_sdk` for error capture.
- `django-redis==5.*` added to requirements + CACHES backend updated in `local.py` and `production.py` from `django.core.cache.backends.redis.RedisCache` to `django_redis.cache.RedisCache` (required for `get_redis_connection("default")`).
- `backend/.env.example` adapted in lieu of `.envs/.local/.django` (file doesn't exist in this project structure) — added `MPESA_ENV`, `MPESA_CONSUMER_KEY`, `MPESA_CONSUMER_SECRET` sandbox placeholders.
- `config/settings/base.py`: added MPESA_* settings + fixed pre-existing `scrub_pii` string-vs-callable bug.
- 15 tests, all pass. flake8 + black + isort clean on new files.

### File List

**New:**
- `backend/apps/payment/daraja.py`
- `backend/apps/payment/tests/test_daraja.py`

**Modified:**
- `backend/requirements/base.txt` — added `requests==2.*`, `django-redis==5.*`
- `backend/config/settings/base.py` — added MPESA_* settings + fixed `scrub_pii` import
- `backend/config/settings/local.py` — updated CACHES to `django_redis.cache.RedisCache`
- `backend/config/settings/production.py` — updated CACHES to `django_redis.cache.RedisCache`
- `backend/.env.example` — added MPESA_* sandbox placeholder vars

### Change Log

- 2026-03-13: Story 2.1 implemented — all 5 tasks complete, 17 tests pass (post-review), flake8+black+isort clean
- 2026-03-13: Code review — 2 MEDIUM fixed, 3 LOW follow-ups logged; status → done
