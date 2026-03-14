# Story 2.4: STK Push Timeout + EXPIRED Status

Status: done

## Story

As a platform operator,
I want a Celery Beat task to automatically expire STK Push transactions that never received a webhook callback after Safaricom's 5-minute STK Push window closes,
So that stale `STK_PUSH_INITIATED` records are cleaned up proactively and customers see a timely retry prompt instead of a payment stuck in a pending state forever.

## Acceptance Criteria

**AC1 — `expire_stale_stk_pushes` periodic task runs every 2 minutes via Celery Beat**

Given Celery Beat is running with the `CELERY_BEAT_SCHEDULE` configured in `config/settings/base.py`
When 2 minutes elapses
Then `apps.payment.tasks.expire_stale_stk_pushes` is invoked automatically
And the task runs on the `payments.reconciliation` queue

**AC2 — Marks EXPIRED any STK_PUSH_INITIATED transactions older than 5 minutes**

Given one or more `MpesaTransaction` records with `status=STK_PUSH_INITIATED` exist with `initiated_at < now() - 5 minutes`
When `expire_stale_stk_pushes` runs
Then all such records have their `status` set to `EXPIRED`
And `completed_at` is set to `timezone.now()` for each expired record

**AC3 — Too-recent STK_PUSH_INITIATED records are NOT expired**

Given a `MpesaTransaction` with `status=STK_PUSH_INITIATED` and `initiated_at >= now() - 5 minutes`
When `expire_stale_stk_pushes` runs
Then that record's `status` remains `STK_PUSH_INITIATED`
And `completed_at` remains `None`

**AC4 — Already-terminal records are not touched**

Given `MpesaTransaction` records with `status` in `CONFIRMED`, `FAILED`, `EXPIRED`, or `REVERSED` exist with old `initiated_at` timestamps
When `expire_stale_stk_pushes` runs
Then none of those records are modified
And the queryset filter is strictly `status=STK_PUSH_INITIATED`

**AC5 — Batch queryset.update() — not individual saves — for performance**

Given multiple stale `STK_PUSH_INITIATED` records exist
When `expire_stale_stk_pushes` runs
Then a single `queryset.update(status=..., completed_at=...)` call is used
And NOT a Python-level loop with individual `txn.save()` calls
And the count of expired records is captured from the `.update()` return value

**AC6 — Logs the count of expired transactions per run**

Given `expire_stale_stk_pushes` has just run (whether it expired 0 or N records)
When the task completes
Then `log.info("stk_push_expire_run_complete", expired_count=N)` is called
And N is the integer returned from `queryset.update()`

**AC7 — Task is idempotent: safe to run multiple times**

Given `expire_stale_stk_pushes` has already run and expired a set of stale records
When it runs again immediately after (before any new STK pushes are initiated)
Then it expires 0 records
And no already-expired records are re-updated
And the task returns normally with no errors

**AC8 — Celery Beat schedule registered in config/settings/base.py**

Given `config/settings/base.py` defines `CELERY_BEAT_SCHEDULE`
When inspected
Then it contains:
```python
"expire-stale-stk-pushes": {
    "task": "apps.payment.tasks.expire_stale_stk_pushes",
    "schedule": timedelta(minutes=2),
},
```
And `from datetime import timedelta` is imported at the top of the Beat schedule block (or at the module level)

**AC9 — No Daraja API calls — purely DB state management**

Given `expire_stale_stk_pushes` runs
When inspected
Then it makes zero calls to `DarajaClient`, `get_daraja_client()`, or any HTTP endpoint
And it only reads and writes `MpesaTransaction` records in the local database

**AC10 — Task uses @shared_task decorator and DLQ retry pattern**

Given `expire_stale_stk_pushes` is defined in `apps/payment/tasks.py`
When decorated
Then it uses `@shared_task(bind=True, max_retries=5, queue="payments.reconciliation")`
And any unexpected exception triggers `self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))`
And normal execution (even 0 expired) does NOT trigger a retry

**AC11 — All new code passes flake8 (max-line-length=88), isort, and black**

Given all modified files in this story are linted
When `flake8 --max-line-length=88`, `isort --check-only`, and `black --check` are run
Then all checks pass with zero violations

## Tasks / Subtasks

- [x] **Task 1: Add `expire_stale_stk_pushes` task to `apps/payment/tasks.py`** (AC: 1, 2, 3, 4, 5, 6, 7, 9, 10)
  - [x] Add imports at top of file: `from datetime import timedelta`, `from django.utils import timezone`, `from apps.payment.models import MpesaTransaction, MpesaTransactionStatus`
  - [x] Define `_STK_PUSH_TIMEOUT_MINUTES = 5` constant at module level (above the task functions)
  - [x] Implement `expire_stale_stk_pushes(self) -> None` with `@shared_task(bind=True, max_retries=5, queue="payments.reconciliation")`
  - [x] Inside `try` block: compute `cutoff = timezone.now() - timedelta(minutes=_STK_PUSH_TIMEOUT_MINUTES)`
  - [x] Filter `MpesaTransaction.objects.filter(status=MpesaTransactionStatus.STK_PUSH_INITIATED, initiated_at__lt=cutoff)`
  - [x] Call `.update(status=MpesaTransactionStatus.EXPIRED, completed_at=timezone.now())` and capture the integer return value as `expired_count`
  - [x] Call `log.info("stk_push_expire_run_complete", expired_count=expired_count)`
  - [x] Wrap the entire task body in `try/except Exception as exc` and call `self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))`

- [x] **Task 2: Register Beat schedule in `config/settings/base.py`** (AC: 1, 8)
  - [x] Locate the `# Celery` section in `config/settings/base.py` (around line 244–270)
  - [x] Add `CELERY_BEAT_SCHEDULE` dict after the existing `CELERY_TASK_ROUTES` block
  - [x] Import `timedelta` — check whether `from datetime import timedelta` is already present; if not, add it to the top of the settings file (it is a stdlib import, not a Django-specific one)
  - [x] Use the exact key name `"expire-stale-stk-pushes"` for the schedule entry

- [x] **Task 3: Tests in `apps/payment/tests/test_tasks.py`** (AC: 2, 3, 4, 5, 6, 7)
  - [x] `test_stale_records_are_expired` — create a `STK_PUSH_INITIATED` txn with `initiated_at` > 5 min ago (use `MpesaTransaction.objects.filter(...).update(initiated_at=...)` to backdate), run task, assert `status=EXPIRED` and `completed_at` is set
  - [x] `test_recent_records_are_not_expired` — create a fresh `STK_PUSH_INITIATED` txn, run task, assert `status` still `STK_PUSH_INITIATED`
  - [x] `test_confirmed_records_not_touched` — create a `CONFIRMED` txn with old `initiated_at`, run task, assert unchanged
  - [x] `test_failed_records_not_touched` — create a `FAILED` txn with old `initiated_at`, run task, assert unchanged
  - [x] `test_idempotent_second_run` — run task twice, assert second run expires 0 records (patch `log.info` or inspect DB)
  - [x] `test_expired_count_logged` — patch `structlog.get_logger` or use `unittest.mock.patch` on `log.info`; assert `expired_count` value in logged call
  - [x] `test_batch_update_not_individual_save` — patch `MpesaTransaction.save` to ensure it is never called; run task; assert patch was not called
  - [x] Use `@pytest.mark.django_db` for all tests
  - [x] Create `test_tasks.py` as a new file (does not yet exist in `apps/payment/tests/`)

## Dev Notes

### Task Implementation — Full Pattern

```python
# Append to backend/apps/payment/tasks.py

import structlog
from celery import shared_task
from datetime import timedelta
from django.utils import timezone

from apps.payment.models import MpesaTransaction, MpesaTransactionStatus

log = structlog.get_logger(__name__)  # already defined at top of tasks.py

_STK_PUSH_TIMEOUT_MINUTES = 5


@shared_task(bind=True, max_retries=5, queue="payments.reconciliation")
def expire_stale_stk_pushes(self) -> None:
    """Expire STK Push transactions that passed Safaricom's 5-minute window.

    Runs every 2 minutes via Celery Beat. Idempotent — safe to run
    multiple times. Uses queryset.update() for performance (not per-row save).
    No Daraja API calls — purely local DB state management.
    """
    try:
        cutoff = timezone.now() - timedelta(minutes=_STK_PUSH_TIMEOUT_MINUTES)
        expired_count = MpesaTransaction.objects.filter(
            status=MpesaTransactionStatus.STK_PUSH_INITIATED,
            initiated_at__lt=cutoff,
        ).update(
            status=MpesaTransactionStatus.EXPIRED,
            completed_at=timezone.now(),
        )
        log.info("stk_push_expire_run_complete", expired_count=expired_count)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

IMPORTANT: The `log = structlog.get_logger(__name__)` line is already at the top
of `tasks.py` from Story 2.3's additions. Do NOT redeclare it.
Import `MpesaTransaction` and `MpesaTransactionStatus` only once at the top of
`tasks.py` — consolidate all model imports from stories 2.3 and 2.4 together.

### CELERY_BEAT_SCHEDULE in settings/base.py

```python
# ---------------------------------------------------------------------------
# Celery Beat schedule
# ---------------------------------------------------------------------------
from datetime import timedelta  # stdlib — add near top of file if not present

CELERY_BEAT_SCHEDULE = {
    "expire-stale-stk-pushes": {
        "task": "apps.payment.tasks.expire_stale_stk_pushes",
        "schedule": timedelta(minutes=2),
    },
}
```

Note: `config/settings/base.py` currently uses `CELERY_BEAT_SCHEDULER =
"django_celery_beat.schedulers:DatabaseScheduler"`. The `DatabaseScheduler`
reads `CELERY_BEAT_SCHEDULE` from settings AND from the database
`PeriodicTask` table. Defining the schedule in settings is the correct approach
for tasks that should always exist — they will be created in the DB on first
Celery Beat startup via `django_celery_beat`'s `sync_to_db` mechanism.

The `timedelta` import should go at the top of `base.py` with other stdlib
imports. Check if it is already imported before adding it.

### Why 5-Minute Cutoff (not 2 hours)

The `reconcile_payments` task in Story 2.5 handles the reconciliation of
transactions older than 2 hours by querying the Daraja Transaction Status API.
This story's `expire_stale_stk_pushes` handles the much shorter window:
Safaricom's STK Push times out after ~5 minutes of no customer response.
If the customer does not enter their PIN within 5 minutes, Daraja SHOULD send
a webhook with `ResultCode=1037`, but that webhook can be missed (network issues,
server restart during the window). This task is a safety net for those missed
webhooks.

The 5-minute constant is intentionally named `_STK_PUSH_TIMEOUT_MINUTES` (not
hardcoded inline) so it is self-documenting and easy to adjust if Safaricom
changes their timeout policy.

### queryset.update() Timestamp Precision

When calling `queryset.update(completed_at=timezone.now())`, Django evaluates
`timezone.now()` once at the Python level and passes the resulting datetime to
the SQL `UPDATE` statement. All records in the batch will have the same
`completed_at` value. This is acceptable and expected for this use case.

If sub-second precision per-record is required in a future story, use a
`Case/When` expression with `ExpressionWrapper`. For now, a single timestamp
for the batch is correct.

### Test Setup — Backdating initiated_at

`initiated_at` uses `auto_now_add=True` which makes it non-editable via
`MpesaTransaction(initiated_at=...)`. To backdate for tests, use:

```python
# After creating the transaction, backdate via queryset update:
stale_txn = MpesaTransaction.objects.create(
    store=store,
    reference="ORDER-STALE",
    phone="+254712345678",
    amount="100.00",
    status=MpesaTransactionStatus.STK_PUSH_INITIATED,
    checkout_request_id="ws_CO_stale123",
    merchant_request_id="29115-stale-1",
)
# Backdate to 10 minutes ago — past the 5-minute cutoff
MpesaTransaction.objects.filter(pk=stale_txn.pk).update(
    initiated_at=timezone.now() - timedelta(minutes=10)
)
stale_txn.refresh_from_db()
```

This pattern bypasses `auto_now_add` by going directly to SQL UPDATE.

### Testing the Beat Schedule (not required for this story)

Do NOT write a test that actually waits for Celery Beat to trigger the task —
that requires a live Celery worker + beat process and is an integration test
outside the scope of the unit test suite.

Test the schedule registration by asserting `CELERY_BEAT_SCHEDULE` contains
the expected entry in a settings test. Or simply trust that the `expire_stale_stk_pushes`
unit tests cover the task behavior and leave schedule registration to the
integration/smoke tests already in `core/tests/test_smoke.py`.

### Files to Create / Modify

| File | Action |
|---|---|
| `backend/apps/payment/tasks.py` | **MODIFY** — append `expire_stale_stk_pushes` task + `_STK_PUSH_TIMEOUT_MINUTES` constant |
| `backend/config/settings/base.py` | **MODIFY** — add `CELERY_BEAT_SCHEDULE` with `expire-stale-stk-pushes` entry |
| `backend/apps/payment/tests/test_tasks.py` | **CREATE** — 7 task unit tests |

### Project Structure Notes

- `apps/payment/tasks.py` already has `reconcile_payment` stub and (after Story 2.3) `process_mpesa_callback`. Append `expire_stale_stk_pushes` at the end of the file. The `log`, `MpesaTransaction`, `MpesaTransactionStatus` imports from Story 2.3 should already be in the file — do NOT duplicate them.
- `config/settings/base.py` currently has `CELERY_BEAT_SCHEDULER` set but no `CELERY_BEAT_SCHEDULE` dict. This story adds the schedule dict for the first time.
- `apps/payment/tests/test_tasks.py` does not exist yet — this story creates it.
- Existing test files: `test_daraja.py` (Story 2.1), `test_stk_push.py` (Story 2.2), `test_webhook.py` (Story 2.3). Test naming follows the `test_<module>.py` convention.
- flake8 max-line-length=88 (from `setup.cfg`).
- isort: stdlib imports (`from datetime import timedelta`) go in the STDLIB section, above Django imports.

### References

- FR37 (daily reconcile_payments task): `_bmad-output/planning-artifacts/epics.md` line 69
- FR39 (STK Push timeout → EXPIRED): `_bmad-output/planning-artifacts/epics.md` line 71
- FR47 (DLQ + exponential backoff): `_bmad-output/planning-artifacts/epics.md` line 85
- FR48 (Celery Beat schedule): `_bmad-output/planning-artifacts/epics.md` line 86
- Story 2.4 spec: `_bmad-output/planning-artifacts/epics.md` line 902
- Architecture — CELERY_BEAT_SCHEDULER setting: `backend/config/settings/base.py` line 248
- Architecture — exponential backoff pattern: `_bmad-output/planning-artifacts/architecture.md` line 469
- Architecture — payments.reconciliation queue: `_bmad-output/planning-artifacts/architecture.md` line 472
- Existing tasks.py: `backend/apps/payment/tasks.py`
- MpesaTransaction model: `backend/apps/payment/models.py`

## Previous Story Learnings (Stories 2.2 + 2.3)

- **`auto_now_add=True` fields cannot be set directly**: Use `queryset.update(initiated_at=...)` in tests to backdate; never try to pass `initiated_at` to the model constructor.
- **`queryset.update()` bypasses model `save()` and signals**: This is intentional here — we do NOT want `post_save` signals firing for batch expiry. If signal firing is needed in future, iterate and call `save()` individually.
- **`log = structlog.get_logger(__name__)` at module level**: Defined once per module, not inside the task function.
- **Celery task `bind=True`**: Provides `self` for `self.request.retries` access in `self.retry()`. Required for the exponential backoff pattern.
- **`@shared_task` vs `@app.task`**: `@shared_task` is the correct decorator for apps — it does not require a direct reference to the Celery app instance.
- **flake8 max-line-length=88**: All lines must fit. Long `queryset.filter(...)` chains may need to be split across lines with backslash continuation or parentheses.
- **`@pytest.mark.django_db`** required for all tests touching ORM — even queryset.update() calls.
- **`transaction=True` for `on_commit` tests** (Story 2.3 learning) — not required for this story since no `on_commit` is used in `expire_stale_stk_pushes`.

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- `timedelta` already imported in `base.py` at line 214 — no duplicate added
- `_STK_PUSH_TIMEOUT_MINUTES = 5` placed after `_EXPIRED_RESULT_CODES` constant for grouping
- `log`, `MpesaTransaction`, `MpesaTransactionStatus` already imported in tasks.py from Story 2.3 — only `from datetime import timedelta` added
- All 7 tests use `@pytest.mark.django_db` (no `transaction=True` needed — no `on_commit` used)
- `_backdate()` helper uses `queryset.update(initiated_at=...)` to bypass `auto_now_add=True`

### Completion Notes List

- `expire_stale_stk_pushes` uses `queryset.update()` (AC5) — single SQL UPDATE for all stale records, no Python loop
- `_STK_PUSH_TIMEOUT_MINUTES = 5` module constant makes the 5-minute window self-documenting
- `CELERY_BEAT_SCHEDULE` added to `config/settings/base.py` after `CELERY_TASK_ROUTES` — uses `timedelta(minutes=2)` for run interval
- All 7 tests cover: stale expiry, recent skip, terminal-status skip (CONFIRMED + FAILED), idempotency, count logging, batch-not-individual-save
- Task wraps logic in `try/except Exception` → `self.retry()` with exponential backoff (AC10)

### File List

- `backend/apps/payment/tasks.py` — MODIFIED: added `from datetime import timedelta`, `_STK_PUSH_TIMEOUT_MINUTES = 5` constant, `expire_stale_stk_pushes` task
- `backend/config/settings/base.py` — MODIFIED: added `CELERY_BEAT_SCHEDULE` with `expire-stale-stk-pushes` entry
- `backend/apps/payment/tests/test_tasks.py` — CREATED: 7-test suite covering AC2–AC7

### Change Log

| Date | Change | Author |
|---|---|---|
| 2026-03-14 | Initial implementation of Story 2.4 — all 3 tasks complete | claude-sonnet-4-6 |
