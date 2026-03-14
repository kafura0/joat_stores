"""
Tests for Story 2.4: expire_stale_stk_pushes Celery task.

Covers:
- AC2: stale STK_PUSH_INITIATED records (>5 min) are set to EXPIRED
- AC3: recent STK_PUSH_INITIATED records (<5 min) are NOT touched
- AC4: already-terminal records (CONFIRMED, FAILED, etc.) are not touched
- AC5: batch queryset.update() is used — no individual txn.save() calls
- AC6: expired_count is logged on every run
- AC7: task is idempotent (second run expires 0 records)

Implementation: Story 2.4
"""

import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest

from django.utils import timezone

from apps.payment.models import MpesaTransaction, MpesaTransactionStatus
from apps.payment.tasks import expire_stale_stk_pushes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_store():
    from apps.store.models import Store

    return Store.objects.create(
        name="Task Test Store",
        slug=f"task-{uuid.uuid4().hex[:8]}",
        domain=f"tasks-{uuid.uuid4().hex[:8]}.joat.com",
        country="KE",
    )


def _make_txn(store, checkout_id=None, status=None):
    if checkout_id is None:
        checkout_id = f"ws_CO_{uuid.uuid4().hex[:12]}"
    if status is None:
        status = MpesaTransactionStatus.STK_PUSH_INITIATED
    return MpesaTransaction.objects.create(
        store=store,
        reference=f"ORDER-{uuid.uuid4().hex[:6]}",
        phone="+254712345678",
        amount="100.00",
        status=status,
        checkout_request_id=checkout_id,
        merchant_request_id=f"29115-{uuid.uuid4().hex[:6]}-1",
    )


def _backdate(txn, minutes):
    """Backdate initiated_at by given minutes (bypasses auto_now_add)."""
    MpesaTransaction.objects.filter(pk=txn.pk).update(
        initiated_at=timezone.now() - timedelta(minutes=minutes)
    )
    txn.refresh_from_db()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_stale_records_are_expired():
    """AC2: STK_PUSH_INITIATED txns older than 5 min are set to EXPIRED."""
    store = _make_store()
    txn = _make_txn(store)
    _backdate(txn, minutes=10)

    expire_stale_stk_pushes()

    txn.refresh_from_db()
    assert txn.status == MpesaTransactionStatus.EXPIRED
    assert txn.completed_at is not None


@pytest.mark.django_db
def test_recent_records_are_not_expired():
    """AC3: STK_PUSH_INITIATED txns within 5 min are NOT expired."""
    store = _make_store()
    txn = _make_txn(store)
    # initiated_at is auto_now_add — less than 1 minute old, well within window

    expire_stale_stk_pushes()

    txn.refresh_from_db()
    assert txn.status == MpesaTransactionStatus.STK_PUSH_INITIATED
    assert txn.completed_at is None


@pytest.mark.django_db
def test_confirmed_records_not_touched():
    """AC4: CONFIRMED txns with old initiated_at are not modified."""
    store = _make_store()
    txn = _make_txn(store, status=MpesaTransactionStatus.CONFIRMED)
    _backdate(txn, minutes=10)

    expire_stale_stk_pushes()

    txn.refresh_from_db()
    assert txn.status == MpesaTransactionStatus.CONFIRMED


@pytest.mark.django_db
def test_failed_records_not_touched():
    """AC4: FAILED txns with old initiated_at are not modified."""
    store = _make_store()
    txn = _make_txn(store, status=MpesaTransactionStatus.FAILED)
    _backdate(txn, minutes=10)

    expire_stale_stk_pushes()

    txn.refresh_from_db()
    assert txn.status == MpesaTransactionStatus.FAILED


@pytest.mark.django_db
def test_expired_records_not_re_expired():
    """AC4: already-EXPIRED txns with old initiated_at are not modified."""
    store = _make_store()
    txn = _make_txn(store, status=MpesaTransactionStatus.EXPIRED)
    _backdate(txn, minutes=10)

    expire_stale_stk_pushes()

    txn.refresh_from_db()
    assert txn.status == MpesaTransactionStatus.EXPIRED


@pytest.mark.django_db
def test_reversed_records_not_touched():
    """AC4: REVERSED txns with old initiated_at are not modified."""
    store = _make_store()
    txn = _make_txn(store, status=MpesaTransactionStatus.REVERSED)
    _backdate(txn, minutes=10)

    expire_stale_stk_pushes()

    txn.refresh_from_db()
    assert txn.status == MpesaTransactionStatus.REVERSED


@pytest.mark.django_db
def test_idempotent_second_run():
    """AC7: Running the task twice expires 0 records on the second run."""
    store = _make_store()
    txn = _make_txn(store)
    _backdate(txn, minutes=10)

    expire_stale_stk_pushes()
    txn.refresh_from_db()
    assert txn.status == MpesaTransactionStatus.EXPIRED

    # Second run — nothing left to expire
    with patch("apps.payment.tasks.log") as mock_log:
        expire_stale_stk_pushes()
        mock_log.info.assert_called_once_with(
            "stk_push_expire_run_complete", expired_count=0
        )


@pytest.mark.django_db
def test_expired_count_logged():
    """AC6: log.info called with correct expired_count after each run."""
    store = _make_store()
    txn1 = _make_txn(store)
    txn2 = _make_txn(store)
    _backdate(txn1, minutes=10)
    _backdate(txn2, minutes=15)

    with patch("apps.payment.tasks.log") as mock_log:
        expire_stale_stk_pushes()
        mock_log.info.assert_called_once_with(
            "stk_push_expire_run_complete", expired_count=2
        )


@pytest.mark.django_db
def test_no_stale_records_logs_zero():
    """L1: Task logs expired_count=0 when no stale records exist."""
    with patch("apps.payment.tasks.log") as mock_log:
        expire_stale_stk_pushes()
        mock_log.info.assert_called_once_with(
            "stk_push_expire_run_complete", expired_count=0
        )


@pytest.mark.django_db
def test_batch_update_not_individual_save():
    """AC5: MpesaTransaction.save() is never called — only queryset.update()."""
    store = _make_store()
    txn = _make_txn(store)
    _backdate(txn, minutes=10)

    with patch.object(MpesaTransaction, "save") as mock_save:
        expire_stale_stk_pushes()
        mock_save.assert_not_called()

    txn.refresh_from_db()
    assert txn.status == MpesaTransactionStatus.EXPIRED
