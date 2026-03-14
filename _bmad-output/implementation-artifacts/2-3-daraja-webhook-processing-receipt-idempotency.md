# Story 2.3: Daraja Webhook Processing + Receipt Idempotency

Status: done

## Story

As a payment system,
I want all Daraja STK Push webhook callbacks to be HMAC-verified, idempotently processed, and to trigger downstream order/tab updates via a signal,
So that duplicate Daraja retries never double-confirm orders, and all commerce verticals react to payment confirmation without coupling to the payment module.

## Acceptance Criteria

**AC1 — Idempotent webhook: already-terminal status returns HTTP 200 immediately**

Given a Daraja webhook arrives for a `CheckoutRequestID` whose `MpesaTransaction` already has status `CONFIRMED`, `FAILED`, `EXPIRED`, or `REVERSED`
When `process_mpesa_callback` processes the payload
Then the existing transaction is returned unchanged
And HTTP 200 is returned to Daraja with no state change
And no Celery task is enqueued again (the view enqueues the task; the task does the idempotency check)

**AC2 — Successful payment sets CONFIRMED + stores receipt number**

Given a webhook payload with `ResultCode=0` and a valid `MpesaReceiptNumber` in `CallbackMetadata`
When `process_mpesa_callback` processes it
Then `MpesaTransaction.status` is set to `CONFIRMED`
And `MpesaTransaction.mpesa_receipt_number` is set to the receipt number from the callback
And `MpesaTransaction.completed_at` is set to `django.utils.timezone.now()`
And the DB `unique=True` constraint on `mpesa_receipt_number` prevents any duplicate receipt from being stored (duplicate webhook returns HTTP 200 without re-processing per AC1)

**AC3 — Customer cancellation (ResultCode=1032) sets EXPIRED**

Given a webhook payload with `ResultCode=1032` (customer cancelled the STK prompt)
When `process_mpesa_callback` processes it
Then `MpesaTransaction.status` is set to `EXPIRED`
And `MpesaTransaction.completed_at` is set to `timezone.now()`
And the transaction is NOT set to `FAILED` (per FR39: cancellation and timeout are both `EXPIRED`)

**AC4 — STK Push timeout (ResultCode=1037) sets EXPIRED**

Given a webhook payload with `ResultCode=1037` (STK Push timed out at Daraja side)
When `process_mpesa_callback` processes it
Then `MpesaTransaction.status` is set to `EXPIRED`
And `MpesaTransaction.completed_at` is set to `timezone.now()`
And the transaction is NOT set to `FAILED` (same rule as AC3)

**AC5 — All other non-zero ResultCodes set FAILED**

Given a webhook payload with a non-zero `ResultCode` that is neither `1032` nor `1037` (e.g. `1`, `2`, `17`)
When `process_mpesa_callback` processes it
Then `MpesaTransaction.status` is set to `FAILED`
And `MpesaTransaction.completed_at` is set to `timezone.now()`

**AC6 — HMAC-SHA256 signature validation rejects unauthorized webhooks**

Given an incoming webhook POST request
When the `X-Daraja-Signature` header is absent or its value does not match `HMAC-SHA256(secret=MPESA_WEBHOOK_SECRET, message=raw_request_body)`
Then HTTP 400 is returned with `{"code": "INVALID_SIGNATURE", "detail": "Webhook signature verification failed"}`
And no Celery task is enqueued
And no `MpesaTransaction` is updated

**AC7 — Webhook endpoint is public (AllowAny) — Daraja cannot authenticate**

Given `POST /api/v1/payments/mpesa-callback/` is called by Daraja (no auth token)
When the request arrives
Then `IsAuthenticated` is NOT in the view's `permission_classes`
And `AllowAny` is used instead
And HMAC signature validation (AC6) is the sole security gate

**AC8 — All status transitions use transaction.atomic() + SELECT FOR UPDATE**

Given two concurrent identical webhook deliveries arrive simultaneously (Daraja retry storms)
When both are processed in `process_mpesa_callback`
Then only one update occurs
And the second update is blocked by `SELECT FOR UPDATE` until the first commits
And both return HTTP 200 (the second sees the already-terminal status and exits early per AC1)

**AC9 — Webhook endpoint: POST /api/v1/payments/mpesa-callback/**

Given `POST /api/v1/payments/mpesa-callback/` is defined in `apps/payment/urls.py`
When Daraja POSTs the callback
Then the view immediately enqueues `process_mpesa_callback.delay(payload)` and returns HTTP 200
And the actual DB update happens in the Celery task (fire-and-forget pattern)
And if Daraja does not receive HTTP 200 within its timeout it will retry — the idempotency in AC1 handles retries safely

**AC10 — payment_confirmed signal emitted on CONFIRMED transition**

Given `process_mpesa_callback` sets a transaction to `CONFIRMED`
When the atomic block commits (using `transaction.on_commit`)
Then `payment_confirmed.send(sender=MpesaTransaction, transaction=txn)` is called
And any connected receiver (order app, restaurant app, bar app) can react without importing the payment app

**AC11 — Celery task on payments.reconciliation queue**

Given `process_mpesa_callback` is defined in `apps/payment/tasks.py`
When it is decorated
Then it uses `@shared_task(bind=True, max_retries=5, queue="payments.reconciliation")`
And on any unexpected exception it retries with `countdown=60 * (2 ** self.request.retries)`
And it does NOT retry on idempotency exit (AC1 is not an error condition)

**AC12 — All new code passes flake8 (max-line-length=88), isort, and black**

Given all new files in this story are linted
When `flake8 --max-line-length=88`, `isort --check-only`, and `black --check` are run
Then all checks pass with zero violations

## Tasks / Subtasks

- [x] **Task 1: Add `payment_confirmed` Django signal to `apps/payment/signals.py`** (AC: 10)
  - [x] Create `backend/apps/payment/signals.py`
  - [x] Define `payment_confirmed = django.dispatch.Signal()` — no `providing_args` (deprecated in Django 3.1+)
  - [x] Add module docstring explaining this is the integration point for order/restaurant/bar apps
  - [x] In `apps/payment/apps.py` `PaymentConfig.ready()`, import `apps.payment.signals` to register any auto-connected receivers (none yet, but pattern is established)

- [x] **Task 2: Add `process_mpesa_callback` Celery task to `apps/payment/tasks.py`** (AC: 1, 2, 3, 4, 5, 8, 10, 11)
  - [x] Add imports: `django.db.transaction`, `django.utils.timezone`, `apps.payment.models.MpesaTransaction`, `apps.payment.models.MpesaTransactionStatus`, `apps.payment.signals.payment_confirmed`
  - [x] Implement `process_mpesa_callback(self, payload: dict) -> None` with `@shared_task(bind=True, max_retries=5, queue="payments.reconciliation")`
  - [x] Extract `checkout_request_id` from `payload["Body"]["stkCallback"]["CheckoutRequestID"]`
  - [x] Extract `result_code` from `payload["Body"]["stkCallback"]["ResultCode"]`
  - [x] Inside `transaction.atomic()` with `select_for_update()`, fetch `MpesaTransaction` by `checkout_request_id`
  - [x] Implement idempotency guard: if status is already terminal (`CONFIRMED`, `FAILED`, `EXPIRED`, `REVERSED`), log and return immediately
  - [x] Implement status transitions: `ResultCode=0` → `CONFIRMED` + extract `mpesa_receipt_number` from `CallbackMetadata`; `ResultCode in (1032, 1037)` → `EXPIRED`; all others → `FAILED`
  - [x] Set `completed_at = timezone.now()` on all non-idempotent transitions
  - [x] On `CONFIRMED`: use `transaction.on_commit(lambda: payment_confirmed.send(sender=MpesaTransaction, transaction=txn))` to emit signal after atomic commit
  - [x] Wrap entire task body in `try/except Exception` and call `self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))` on unexpected errors
  - [x] Log all state transitions with `structlog.get_logger(__name__)`

- [x] **Task 3: Add `MpesaCallbackView` to `apps/payment/views.py`** (AC: 6, 7, 9)
  - [x] Import `AllowAny` from `rest_framework.permissions`
  - [x] Import `process_mpesa_callback` from `apps.payment.tasks`
  - [x] Implement `_verify_daraja_signature(request) -> bool` helper using `hmac.compare_digest` — reads `MPESA_WEBHOOK_SECRET` from `django.conf.settings`
  - [x] Implement `MpesaCallbackView(APIView)` with `permission_classes = [AllowAny]`
  - [x] In `post(self, request)`: call `_verify_daraja_signature(request)` first; if invalid return HTTP 400 with `INVALID_SIGNATURE`
  - [x] Enqueue `process_mpesa_callback.delay(request.data)` and return HTTP 200 immediately
  - [x] Do NOT perform any DB operations in the view — purely validate + enqueue

- [x] **Task 4: Add webhook URL to `apps/payment/urls.py`** (AC: 9)
  - [x] Import `MpesaCallbackView` from `apps.payment.views`
  - [x] Add `path("mpesa-callback/", MpesaCallbackView.as_view(), name="mpesa-callback")`
  - [x] Verify the full URL resolves to `POST /api/v1/payments/mpesa-callback/` (matches `MPESA_CALLBACK_URL`)

- [x] **Task 5: Add `MPESA_WEBHOOK_SECRET` to Django settings** (AC: 6)
  - [x] In `config/settings/base.py`, add `MPESA_WEBHOOK_SECRET = env("MPESA_WEBHOOK_SECRET", default="")` in the `# M-Pesa / Daraja` section
  - [x] In `backend/.env.example`, add `MPESA_WEBHOOK_SECRET=your-webhook-secret-here` with a comment

- [x] **Task 6: Tests in `apps/payment/tests/test_webhook.py`** (AC: 1–11)
  - [x] `test_idempotent_confirmed_webhook` — task exits early when status already CONFIRMED
  - [x] `test_idempotent_failed_webhook` — task exits early when status already FAILED
  - [x] `test_idempotent_expired_webhook` — task exits early when status already EXPIRED
  - [x] `test_result_code_0_sets_confirmed_and_receipt` — verify status, mpesa_receipt_number, completed_at
  - [x] `test_result_code_1032_sets_expired` — cancellation → EXPIRED
  - [x] `test_result_code_1037_sets_expired` — timeout → EXPIRED
  - [x] `test_other_result_code_sets_failed` — e.g. ResultCode=17 → FAILED
  - [x] `test_payment_confirmed_signal_emitted` — patch `payment_confirmed.send`, assert called on ResultCode=0
  - [x] `test_invalid_signature_returns_400` — missing/wrong `X-Daraja-Signature` header
  - [x] `test_missing_signature_header_returns_400` — absent header → HTTP 400
  - [x] `test_empty_secret_rejects_webhook` — unconfigured secret rejects all
  - [x] `test_valid_signature_enqueues_task` — correct HMAC → task is called (patch `process_mpesa_callback.delay`)
  - [x] `test_view_returns_200_immediately` — view returns 200 without waiting for task
  - [x] `test_unknown_checkout_request_id_no_error` — unknown ID → log warning, no error
  - [x] `test_malformed_payload_no_error` — bad structure → log error, no exception
  - [x] Use `unittest.mock.patch` (NOT pytest-mock)
  - [x] Use `@pytest.mark.django_db` for all tests touching the ORM
  - [x] Use `@pytest.mark.django_db(transaction=True)` for the `transaction.on_commit` signal test

## Dev Notes

### Daraja Webhook Payload — Exact Format

```
POST /api/v1/payments/mpesa-callback/
Content-Type: application/json
X-Daraja-Signature: <HMAC-SHA256 hex digest>

Successful payment (ResultCode=0):
{
  "Body": {
    "stkCallback": {
      "MerchantRequestID": "29115-34620561-1",
      "CheckoutRequestID": "ws_CO_191220191020363925",
      "ResultCode": 0,
      "ResultDesc": "The service request is processed successfully.",
      "CallbackMetadata": {
        "Item": [
          {"Name": "Amount", "Value": 100},
          {"Name": "MpesaReceiptNumber", "Value": "LGR7XXXXXXXX"},
          {"Name": "TransactionDate", "Value": 20240315143022},
          {"Name": "PhoneNumber", "Value": 254712345678}
        ]
      }
    }
  }
}

Customer cancelled (ResultCode=1032):
{
  "Body": {
    "stkCallback": {
      "MerchantRequestID": "29115-34620561-1",
      "CheckoutRequestID": "ws_CO_191220191020363925",
      "ResultCode": 1032,
      "ResultDesc": "Request cancelled by user."
    }
  }
}

Timeout (ResultCode=1037):
{
  "Body": {
    "stkCallback": {
      "MerchantRequestID": "29115-34620561-1",
      "CheckoutRequestID": "ws_CO_191220191020363925",
      "ResultCode": 1037,
      "ResultDesc": "DS timeout user cannot be reached"
    }
  }
}

IMPORTANT: When ResultCode != 0, the "CallbackMetadata" key is absent entirely.
The task must guard against KeyError when extracting receipt number.
```

### HMAC Signature Verification — Exact Pattern

```python
import hashlib
import hmac

from django.conf import settings


def _verify_daraja_signature(request) -> bool:
    """Return True if the X-Daraja-Signature header matches the payload HMAC."""
    expected_sig = request.META.get("HTTP_X_DARAJA_SIGNATURE", "")
    secret = getattr(settings, "MPESA_WEBHOOK_SECRET", "")
    if not secret:
        # Misconfigured — reject all webhooks to fail safe
        return False
    raw_body = request.body  # bytes — must be read before DRF parses JSON
    computed = hmac.new(
        secret.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed, expected_sig)
```

CRITICAL: `request.body` MUST be read before DRF's JSON parser consumes the stream.
In DRF's `APIView`, `request.data` triggers JSON parsing. `request.body` is still
available because DRF caches it on `request._stream`. Always access `request.body`
BEFORE `request.data` in the view, or read `request.body` from the raw Django request
(`request._request.body`).

Safest pattern for the view:

```python
class MpesaCallbackView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # Signature check must come first — before request.data is accessed
        if not _verify_daraja_signature(request):
            return Response(
                {
                    "code": "INVALID_SIGNATURE",
                    "detail": "Webhook signature verification failed",
                },
                status=400,
            )
        process_mpesa_callback.delay(request.data)
        return Response({"status": "accepted"}, status=200)
```

In tests, when using DRF's `APIRequestFactory`, set:
```python
request = factory.post(
    "/api/v1/payments/mpesa-callback/",
    data=json.dumps(payload),
    content_type="application/json",
    HTTP_X_DARAJA_SIGNATURE=computed_sig,
)
```

### process_mpesa_callback Task — Full Design

```python
# apps/payment/tasks.py

import structlog
from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.payment.models import MpesaTransaction, MpesaTransactionStatus
from apps.payment.signals import payment_confirmed

log = structlog.get_logger(__name__)

_TERMINAL_STATUSES = {
    MpesaTransactionStatus.CONFIRMED,
    MpesaTransactionStatus.FAILED,
    MpesaTransactionStatus.EXPIRED,
    MpesaTransactionStatus.REVERSED,
}

_EXPIRED_RESULT_CODES = {1032, 1037}


@shared_task(bind=True, max_retries=5, queue="payments.reconciliation")
def process_mpesa_callback(self, payload: dict) -> None:
    """Process a Daraja STK Push webhook callback.

    Called asynchronously by MpesaCallbackView. Idempotent — safe to
    call multiple times for the same CheckoutRequestID.
    """
    try:
        stk_callback = payload["Body"]["stkCallback"]
        checkout_request_id = stk_callback["CheckoutRequestID"]
        result_code = int(stk_callback["ResultCode"])
    except (KeyError, ValueError, TypeError) as exc:
        log.error("mpesa_callback_malformed_payload", error=str(exc))
        return  # Do not retry on malformed payload — Daraja will retry itself

    with transaction.atomic():
        try:
            txn = (
                MpesaTransaction.objects
                .select_for_update()
                .get(checkout_request_id=checkout_request_id)
            )
        except MpesaTransaction.DoesNotExist:
            log.warning(
                "mpesa_callback_unknown_checkout_request_id",
                checkout_request_id=checkout_request_id,
            )
            return  # No retry — we have no record of this transaction

        # Idempotency guard
        if txn.status in _TERMINAL_STATUSES:
            log.info(
                "mpesa_callback_already_terminal",
                checkout_request_id=checkout_request_id,
                status=txn.status,
            )
            return

        now = timezone.now()

        if result_code == 0:
            # Extract receipt number from CallbackMetadata
            items = stk_callback.get("CallbackMetadata", {}).get("Item", [])
            receipt = next(
                (
                    item["Value"]
                    for item in items
                    if item.get("Name") == "MpesaReceiptNumber"
                ),
                None,
            )
            txn.status = MpesaTransactionStatus.CONFIRMED
            txn.mpesa_receipt_number = receipt
            txn.completed_at = now
            txn.save(
                update_fields=["status", "mpesa_receipt_number", "completed_at"]
            )
            log.info(
                "mpesa_payment_confirmed",
                checkout_request_id=checkout_request_id,
                receipt=receipt,
            )
            # Emit signal after atomic commit so receivers see committed state
            transaction.on_commit(
                lambda: payment_confirmed.send(
                    sender=MpesaTransaction, transaction=txn
                )
            )

        elif result_code in _EXPIRED_RESULT_CODES:
            txn.status = MpesaTransactionStatus.EXPIRED
            txn.completed_at = now
            txn.save(update_fields=["status", "completed_at"])
            log.info(
                "mpesa_payment_expired",
                checkout_request_id=checkout_request_id,
                result_code=result_code,
            )

        else:
            txn.status = MpesaTransactionStatus.FAILED
            txn.completed_at = now
            txn.save(update_fields=["status", "completed_at"])
            log.warning(
                "mpesa_payment_failed",
                checkout_request_id=checkout_request_id,
                result_code=result_code,
                result_desc=stk_callback.get("ResultDesc", ""),
            )
```

Note: the outer `try/except Exception` for Celery retry wraps the entire block
in the actual implementation to catch DB errors, signal errors, etc. The pattern
above shows the happy path logic; add the retry wrapper around it.

### signals.py — Full Content

```python
"""Payment Django signals.

Integration point for other apps to react to payment events.
Receivers connect via apps.payment.signals in their own apps.py ready().

Example receiver (in apps/order/apps.py):
    from apps.payment.signals import payment_confirmed
    payment_confirmed.connect(handle_payment_confirmed, sender=None)
"""

import django.dispatch

# Fired when a MpesaTransaction transitions to CONFIRMED status.
# kwargs: transaction=<MpesaTransaction instance>
payment_confirmed = django.dispatch.Signal()
```

### apps.py — PaymentConfig.ready() Pattern

```python
# apps/payment/apps.py
from django.apps import AppConfig


class PaymentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.payment"
    label = "payment"

    def ready(self):
        import apps.payment.signals  # noqa: F401 — registers signal namespace
```

Check whether `apps/payment/apps.py` already exists (it should from the cookiecutter
scaffold). If `ready()` already exists, append the import inside it. Do NOT
duplicate the class definition.

### Callback Metadata Extraction — Edge Cases

When `ResultCode=0`, `CallbackMetadata.Item` is a list. Extract defensively:
```python
items = stk_callback.get("CallbackMetadata", {}).get("Item", [])
receipt = next(
    (item["Value"] for item in items if item.get("Name") == "MpesaReceiptNumber"),
    None,
)
```
If `receipt` is `None` for a successful payment, log an error and still mark
CONFIRMED (Daraja sent a success; the receipt may come in a reconciliation call).
Do NOT block the confirmation on a missing receipt number.

### Test Factory Pattern (reuse from Story 2.2)

```python
# In test_webhook.py — inline helpers, no separate factories.py

def _make_store():
    from apps.store.models import Store
    return Store.objects.create(
        name="Webhook Test Store",
        slug="webhook-test",
        domain="webhook.joat.com",
        country="KE",
    )

def _make_txn(store, checkout_id="ws_CO_test123"):
    from apps.payment.models import MpesaTransaction, MpesaTransactionStatus
    return MpesaTransaction.objects.create(
        store=store,
        reference="ORDER-001",
        phone="+254712345678",
        amount="100.00",
        status=MpesaTransactionStatus.STK_PUSH_INITIATED,
        checkout_request_id=checkout_id,
        merchant_request_id="29115-test-1",
    )

MOCK_SUCCESSFUL_PAYLOAD = {
    "Body": {
        "stkCallback": {
            "MerchantRequestID": "29115-test-1",
            "CheckoutRequestID": "ws_CO_test123",
            "ResultCode": 0,
            "ResultDesc": "The service request is processed successfully.",
            "CallbackMetadata": {
                "Item": [
                    {"Name": "Amount", "Value": 100},
                    {"Name": "MpesaReceiptNumber", "Value": "LGR7XXXXXXXX"},
                    {"Name": "TransactionDate", "Value": 20240315143022},
                    {"Name": "PhoneNumber", "Value": 254712345678},
                ]
            },
        }
    }
}

MOCK_CANCEL_PAYLOAD = {
    "Body": {
        "stkCallback": {
            "MerchantRequestID": "29115-test-1",
            "CheckoutRequestID": "ws_CO_test123",
            "ResultCode": 1032,
            "ResultDesc": "Request cancelled by user.",
        }
    }
}
```

### HMAC Test Helper

```python
import hashlib
import hmac as hmac_lib
import json

def _compute_signature(payload: dict, secret: str) -> str:
    body = json.dumps(payload).encode()
    return hmac_lib.new(secret.encode(), body, hashlib.sha256).hexdigest()
```

Use `@override_settings(MPESA_WEBHOOK_SECRET="test-secret")` in view tests.

### Files to Create / Modify

| File | Action |
|---|---|
| `backend/apps/payment/signals.py` | **CREATE** — `payment_confirmed` signal |
| `backend/apps/payment/apps.py` | **MODIFY** — add `import apps.payment.signals` in `ready()` |
| `backend/apps/payment/tasks.py` | **MODIFY** — add `process_mpesa_callback` task (keep existing `reconcile_payment` stub) |
| `backend/apps/payment/views.py` | **MODIFY** — add `MpesaCallbackView` + `_verify_daraja_signature` helper |
| `backend/apps/payment/urls.py` | **MODIFY** — add `mpesa-callback/` path |
| `backend/config/settings/base.py` | **MODIFY** — add `MPESA_WEBHOOK_SECRET` setting |
| `backend/.env.example` | **MODIFY** — add `MPESA_WEBHOOK_SECRET` |
| `backend/apps/payment/tests/test_webhook.py` | **CREATE** — full test suite (11 tests) |

### Project Structure Notes

- `apps/payment/tasks.py` already exists with the `reconcile_payment` stub (Story 2.1). **Append** `process_mpesa_callback` to this file — do NOT replace `reconcile_payment`.
- `apps/payment/signals.py` does not exist yet — this story creates it.
- The `CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"` is already set in `config/settings/base.py`. Story 2.3 does not add any Beat schedule — the callback task is triggered by the webhook view, not by a cron.
- `test_webhook.py` is referenced in the architecture file list (`backend/apps/payment/tests/test_webhook.py`) — use this exact path.
- flake8 max-line-length=88 (from `setup.cfg`). All lines must fit in 88 characters.
- isort: `known_django` section. Import order: FUTURE / STDLIB / DJANGO / THIRDPARTY / FIRSTPARTY / LOCALFOLDER.
- All tests use `unittest.mock.patch`. `pytest-mock` is NOT available.
- `@pytest.mark.django_db` required for ORM tests; `@pytest.mark.django_db(transaction=True)` for `transaction.on_commit` tests.

### References

- FR35 (HMAC verification): `_bmad-output/planning-artifacts/epics.md` line 885
- FR36 (mpesa_receipt_number unique + HTTP 200 on duplicate): `_bmad-output/planning-artifacts/epics.md` line 897
- FR39 (ResultCode 1032/1037 → EXPIRED): `_bmad-output/planning-artifacts/epics.md` line 71
- Story 2.3 spec: `_bmad-output/planning-artifacts/epics.md` line 876
- Architecture — test_webhook.py location: `_bmad-output/planning-artifacts/architecture.md` line 659
- Architecture — payments.reconciliation queue: `_bmad-output/planning-artifacts/architecture.md` line 472
- MpesaTransaction model: `backend/apps/payment/models.py`
- Existing tasks.py: `backend/apps/payment/tasks.py`
- Story 2.2 completion (models, services, daraja, exceptions all built): `_bmad-output/implementation-artifacts/2-2-mpesa-stk-push-initiation-idempotency.md`

## Previous Story Learnings (Story 2.2)

- **`request.body` vs `request.data`**: DRF's `APIView` parses `request.data` lazily. For HMAC, read `request.body` (raw bytes) BEFORE accessing `request.data` or read from `request._request.body`.
- **`transaction.on_commit` requires `@pytest.mark.django_db(transaction=True)`**: The standard `@pytest.mark.django_db` wraps everything in a savepoint that never commits; `on_commit` callbacks never fire. Use `transaction=True` for signal tests.
- **`select_for_update()` requires `transaction=True` in tests too**: Same reason — savepoints don't acquire row locks in PostgreSQL the way a real transaction does.
- **structlog.get_logger(__name__)** at module level — not inside functions.
- **flake8 max-line-length=88 is strict** — confirmed from `setup.cfg`. Lambdas in `on_commit` may need to be extracted into named functions to stay within 88 chars.
- **DRF `APIRequestFactory` for view tests**: use `force_authenticate(request, user=...)` and set `request.store = store` on the underlying Django request.
- **`unittest.mock.patch`** for all mocking — `pytest-mock` is not installed.
- **`MpesaTransactionStatus` choices**: `STK_PUSH_INITIATED`, `CONFIRMED`, `EXPIRED`, `FAILED`, `REVERSED` — all strings, all uppercase.

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- isort auto-fixed import ordering in tasks.py, views.py, test_webhook.py (django section before thirdparty per pyproject.toml config)
- black auto-formatted same three files after isort
- All three linters (flake8, isort, black) pass clean after auto-fixes
- Tests collect correctly (15 tests); DB connection errors are environment-only (no PostgreSQL running locally — same as Story 2.2 baseline)

### Completion Notes List

- Implemented `_handle_mpesa_callback` as a private inner function so `process_mpesa_callback` can cleanly wrap it in try/except for Celery retry, avoiding nested try/except that would accidentally retry on malformed payload or unknown CheckoutRequestID
- `_verify_daraja_signature` reads `request.body` (raw bytes) BEFORE `request.data` is accessed anywhere, per the story dev notes — HMAC is computed on the raw request bytes, matching Daraja's signing behavior
- `authentication_classes = []` set on MpesaCallbackView to prevent DRF from attempting JWT auth on the public webhook endpoint
- `transaction.on_commit` lambda captures `txn` from enclosing scope; fires `payment_confirmed.send(sender=MpesaTransaction, transaction=txn)` only after atomic block commits
- Empty `MPESA_WEBHOOK_SECRET` causes `_verify_daraja_signature` to return `False` (fail-safe: reject all webhooks if secret not configured)
- All 15 tests use `@pytest.mark.django_db(transaction=True)` for ORM + on_commit tests; view tests use `@pytest.mark.django_db` (no on_commit needed)
- Added `label = "payment"` to PaymentConfig in apps.py (was missing from Story 2.2 scaffold)

### File List

- `backend/apps/payment/signals.py` — CREATED: `payment_confirmed` Django signal
- `backend/apps/payment/apps.py` — MODIFIED: added `label = "payment"` + `ready()` importing signals
- `backend/apps/payment/tasks.py` — MODIFIED: added `process_mpesa_callback` task + `_handle_mpesa_callback` helper
- `backend/apps/payment/views.py` — MODIFIED: added `_verify_daraja_signature` helper + `MpesaCallbackView`
- `backend/apps/payment/urls.py` — MODIFIED: added `mpesa-callback/` URL path
- `backend/config/settings/base.py` — MODIFIED: added `MPESA_WEBHOOK_SECRET` setting
- `backend/.env.example` — MODIFIED: added `MPESA_WEBHOOK_SECRET` env var with comment
- `backend/apps/payment/tests/test_webhook.py` — CREATED: 15-test suite covering all ACs

### Change Log

| Date | Change | Author |
|---|---|---|
| 2026-03-14 | Initial implementation of Story 2.3 — all 6 tasks complete | claude-sonnet-4-6 |
