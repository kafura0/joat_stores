"""
Tests for Epic 6 — Contracting Module.

Story 6.1: Service catalog CRUD
Story 6.2: Booking + availability
Story 6.3: Quote request → quote → accept/reject
Story 6.4: Job state machine + milestones
Story 6.5: Invoice generation + shareable token
Story 6.6: Invoice payment + signal auto-settle
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.contracting.models import (
    Invoice,
    Job,
    Quote,
    QuoteRequest,
    Service,
    ServiceBooking,
    _generate_invoice_token,
    _verify_invoice_token,
)
from apps.store.tests.factories import StoreFactory
from apps.users.tests.factories import UserFactory


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store(db):
    return StoreFactory()


@pytest.fixture
def staff(store):
    return UserFactory(store=store, role="store_owner")


@pytest.fixture
def client(staff, store):
    c = APIClient()
    c.force_authenticate(user=staff)
    c.credentials(HTTP_X_STORE_ID=str(store.id))
    return c


@pytest.fixture
def service(store):
    return Service.objects.create(
        store=store,
        name="Plumbing Repair",
        description="Fix leaks",
        base_price=Decimal("2500.00"),
        duration_estimate=120,
        category=Service.CATEGORY_PLUMBING,
    )


@pytest.fixture
def slot(store, service):
    from apps.contracting.models import AvailabilitySlot

    return AvailabilitySlot.objects.create(
        store=store,
        service=service,
        start_time=timezone.now() + timedelta(hours=2),
        end_time=timezone.now() + timedelta(hours=4),
    )


@pytest.fixture
def quote_request(store, service):
    return QuoteRequest.objects.create(
        store=store,
        customer_phone="+254700000001",
        description="I need my pipes fixed.",
        service=service,
    )


@pytest.fixture
def quote(store, quote_request):
    q = Quote.objects.create(
        store=store,
        quote_request=quote_request,
        line_items=[{"description": "Pipe repair", "quantity": 1, "unit_price": "3000.00"}],
        total_amount=Decimal("3000.00"),
        valid_until=date.today() + timedelta(days=7),
    )
    quote_request.status = QuoteRequest.STATUS_QUOTED
    quote_request.save(update_fields=["status"])
    return q


@pytest.fixture
def job(store, quote):
    return Job.objects.create(
        store=store,
        quote=quote,
        title="Plumbing job",
        description="Fix the pipes",
        status=Job.STATUS_PENDING,
    )


# ---------------------------------------------------------------------------
# Story 6.1 — Service catalog
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestServiceCatalog:

    def test_create_service(self, client, store):
        resp = client.post(
            "/api/v1/contracting/services/",
            {
                "name": "Electrical Wiring",
                "description": "Full rewire",
                "base_price": "5000.00",
                "duration_estimate": 240,
                "category": "electrical",
                "is_active": True,
            },
            format="json",
        )
        assert resp.status_code == 201
        assert Service.objects.filter(store=store, name="Electrical Wiring").exists()

    def test_list_services_public(self, store, service):
        c = APIClient()
        c.credentials(HTTP_X_STORE_ID=str(store.id))
        resp = c.get("/api/v1/contracting/services/")
        assert resp.status_code == 200
        assert len(resp.data["data"]) == 1

    def test_inactive_services_excluded(self, client, store):
        Service.objects.create(
            store=store, name="Old", base_price="1000.00", duration_estimate=60,
            is_active=False,
        )
        resp = client.get("/api/v1/contracting/services/")
        # Only active services returned
        for svc in resp.data["data"]:
            assert svc["is_active"] is True


# ---------------------------------------------------------------------------
# Story 6.2 — Bookings
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBookings:

    def test_create_booking_marks_slot_booked(self, client, store, service, slot):
        resp = client.post(
            "/api/v1/contracting/bookings/",
            {
                "customer_phone": "+254700000001",
                "customer_name": "Jane",
                "slot_id": str(slot.id),
            },
            format="json",
        )
        assert resp.status_code == 201
        slot.refresh_from_db()
        assert slot.is_booked is True

    def test_double_booking_returns_409(self, client, store, service, slot):
        # First booking
        client.post(
            "/api/v1/contracting/bookings/",
            {"customer_phone": "+254700000001", "slot_id": str(slot.id)},
            format="json",
        )
        # Second attempt
        resp = client.post(
            "/api/v1/contracting/bookings/",
            {"customer_phone": "+254700000002", "slot_id": str(slot.id)},
            format="json",
        )
        assert resp.status_code == 409

    def test_confirm_booking(self, client, store, service, slot):
        booking = ServiceBooking.objects.create(
            store=store,
            service=service,
            slot=slot,
            customer_phone="+254700000001",
        )
        with patch("apps.contracting.views.send_booking_confirmation") as mock_task:
            mock_task.delay.return_value = None
            resp = client.patch(f"/api/v1/contracting/bookings/{booking.id}/confirm/")
        assert resp.status_code == 200
        booking.refresh_from_db()
        assert booking.status == ServiceBooking.STATUS_CONFIRMED

    def test_availability_returns_unbooked_slots(self, client, store, service, slot):
        resp = client.get(f"/api/v1/contracting/services/{service.id}/availability/")
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_booked_slot_excluded_from_availability(self, client, store, service, slot):
        slot.is_booked = True
        slot.save(update_fields=["is_booked"])
        resp = client.get(f"/api/v1/contracting/services/{service.id}/availability/")
        assert resp.data == []


# ---------------------------------------------------------------------------
# Story 6.3 — Quote flow
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestQuoteFlow:

    def test_create_quote_request(self, client, store, service):
        resp = client.post(
            "/api/v1/contracting/quote-requests/",
            {
                "customer_phone": "+254700000001",
                "description": "Custom tile installation",
                "service": str(service.id),
            },
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["status"] == "OPEN"

    def test_contractor_responds_with_quote(self, client, store, quote_request):
        resp = client.post(
            f"/api/v1/contracting/quote-requests/{quote_request.id}/quote/",
            {
                "line_items": [{"description": "Labour", "quantity": 2, "unit_price": "1500.00"}],
                "total_amount": "3000.00",
                "valid_until": str(date.today() + timedelta(days=14)),
            },
            format="json",
        )
        assert resp.status_code == 201
        quote_request.refresh_from_db()
        assert quote_request.status == QuoteRequest.STATUS_QUOTED

    def test_accept_quote_creates_job(self, client, store, quote):
        resp = client.patch(f"/api/v1/contracting/quotes/{quote.id}/accept/")
        assert resp.status_code == 200
        assert "job_id" in resp.data
        assert Job.objects.filter(id=resp.data["job_id"]).exists()
        quote.refresh_from_db()
        assert quote.status == Quote.STATUS_ACCEPTED

    def test_reject_quote_no_job_created(self, client, store, quote):
        resp = client.patch(f"/api/v1/contracting/quotes/{quote.id}/reject/")
        assert resp.status_code == 200
        quote.refresh_from_db()
        assert quote.status == Quote.STATUS_REJECTED
        assert not Job.objects.filter(quote=quote).exists()


# ---------------------------------------------------------------------------
# Story 6.4 — Job state machine + milestones
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestJobMilestones:

    def test_job_state_machine_full_path(self, job):
        job.transition(Job.STATUS_IN_PROGRESS)
        assert job.status == Job.STATUS_IN_PROGRESS
        job.transition(Job.STATUS_COMPLETED)
        assert job.status == Job.STATUS_COMPLETED
        assert job.completed_at is not None

    def test_invalid_job_transition_raises(self, job):
        with pytest.raises(ValueError):
            job.transition(Job.STATUS_COMPLETED)  # skip IN_PROGRESS

    def test_job_transition_via_api(self, client, store, job):
        resp = client.patch(
            f"/api/v1/contracting/jobs/{job.id}/transition/",
            {"status": "IN_PROGRESS"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["status"] == "IN_PROGRESS"

    def test_invalid_transition_via_api_returns_422(self, client, store, job):
        resp = client.patch(
            f"/api/v1/contracting/jobs/{job.id}/transition/",
            {"status": "COMPLETED"},
            format="json",
        )
        assert resp.status_code == 422

    def test_milestone_completion_updates_status(self, client, store, job):
        from apps.contracting.models import JobMilestone

        milestone = JobMilestone.objects.create(
            store=store, job=job, title="Site inspection"
        )
        resp = client.patch(
            f"/api/v1/contracting/milestones/{milestone.id}/",
            {"notes": "All clear"},
            format="json",
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Story 6.5 — Invoice + HMAC token
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestInvoice:

    def test_invoice_token_round_trip(self):
        invoice_id = "test-invoice-id-123"
        token = _generate_invoice_token(invoice_id)
        assert _verify_invoice_token(token) == invoice_id

    def test_tampered_token_returns_none(self):
        token = _generate_invoice_token("real-id") + "x"
        assert _verify_invoice_token(token) is None

    def test_create_invoice_for_completed_job(self, client, store, job):
        job.status = Job.STATUS_COMPLETED
        job.save(update_fields=["status"])
        # Add quote with line items
        job.quote.status = Quote.STATUS_ACCEPTED
        job.quote.save(update_fields=["status"])

        with patch("apps.contracting.views.generate_invoice_pdf") as mock_task:
            mock_task.delay.return_value = None
            resp = client.post(f"/api/v1/contracting/jobs/{job.id}/invoice/")

        assert resp.status_code == 201
        assert "shareable_url" in resp.data
        assert Invoice.objects.filter(job=job).exists()

    def test_create_invoice_for_non_completed_job_returns_422(self, client, store, job):
        resp = client.post(f"/api/v1/contracting/jobs/{job.id}/invoice/")
        assert resp.status_code == 422

    def test_duplicate_invoice_returns_409(self, client, store, job):
        job.status = Job.STATUS_COMPLETED
        job.save(update_fields=["status"])
        invoice = Invoice.objects.create(
            store=store, job=job,
            line_items=[], total_amount=Decimal("3000.00"),
        )
        resp = client.post(f"/api/v1/contracting/jobs/{job.id}/invoice/")
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Story 6.6 — Invoice payment + signal
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestInvoicePayment:

    def test_signal_marks_invoice_paid_and_settles_job(self, store, job):
        from apps.contracting.apps import _handle_payment_confirmed
        from apps.payment.tests.factories import MpesaTransactionFactory

        job.status = Job.STATUS_COMPLETED
        job.save(update_fields=["status"])
        invoice = Invoice.objects.create(
            store=store, job=job,
            line_items=[], total_amount=Decimal("3000.00"),
            shareable_token=_generate_invoice_token("inv1"),
        )

        txn = MpesaTransactionFactory(store=store, reference=f"invoice-{invoice.id}")
        _handle_payment_confirmed(sender=None, transaction=txn)

        invoice.refresh_from_db()
        job.refresh_from_db()
        assert invoice.payment_status == Invoice.PAYMENT_STATUS_PAID
        assert invoice.paid_at is not None
        assert job.status == Job.STATUS_SETTLED

    def test_signal_ignores_non_invoice_references(self, store):
        from apps.contracting.apps import _handle_payment_confirmed
        from apps.payment.tests.factories import MpesaTransactionFactory

        txn = MpesaTransactionFactory(store=store, reference="order-xyz")
        # Should not raise
        _handle_payment_confirmed(sender=None, transaction=txn)
