"""
Contracting domain models.

Story 6.1: Service (catalog)
Story 6.2: AvailabilitySlot, ServiceBooking
Story 6.3: QuoteRequest, Quote
Story 6.4: Job, JobMilestone
Story 6.5: Invoice (PDF + shareable link)
Story 6.6: Invoice payment via M-Pesa / card

All models inherit TenantModel (UUID PK, store FK, soft-delete, TenantQuerySet).
"""

import hashlib
import hmac
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from core.models import TenantModel


# ---------------------------------------------------------------------------
# Story 6.1 — Service catalog
# ---------------------------------------------------------------------------


class Service(TenantModel):
    """A service offered by a contracting store."""

    CATEGORY_PLUMBING = "plumbing"
    CATEGORY_ELECTRICAL = "electrical"
    CATEGORY_CLEANING = "cleaning"
    CATEGORY_PAINTING = "painting"
    CATEGORY_LANDSCAPING = "landscaping"
    CATEGORY_OTHER = "other"

    CATEGORY_CHOICES = [
        (CATEGORY_PLUMBING, "Plumbing"),
        (CATEGORY_ELECTRICAL, "Electrical"),
        (CATEGORY_CLEANING, "Cleaning"),
        (CATEGORY_PAINTING, "Painting"),
        (CATEGORY_LANDSCAPING, "Landscaping"),
        (CATEGORY_OTHER, "Other"),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    duration_estimate = models.PositiveIntegerField(
        help_text="Estimated duration in minutes.",
    )
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_OTHER,
        db_index=True,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "name"]
        indexes = [
            models.Index(fields=["store", "is_active"], name="idx_contracting_service_active"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.category})"


# ---------------------------------------------------------------------------
# Story 6.2 — Availability + Booking
# ---------------------------------------------------------------------------


class AvailabilitySlot(TenantModel):
    """A time slot the contractor has marked available for a service."""

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="slots")
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_booked = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["start_time"]
        indexes = [
            models.Index(
                fields=["store", "service", "start_time"],
                name="ct_slot_service_time",
            ),
        ]

    def __str__(self) -> str:
        return f"Slot({self.service.name}, {self.start_time}, booked={self.is_booked})"


class ServiceBooking(TenantModel):
    """A customer booking for a specific service slot."""

    STATUS_PENDING = "PENDING"
    STATUS_CONFIRMED = "CONFIRMED"
    STATUS_CANCELLED = "CANCELLED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="bookings")
    slot = models.OneToOneField(
        AvailabilitySlot,
        on_delete=models.PROTECT,
        related_name="booking",
    )
    customer_phone = models.CharField(max_length=20)
    customer_name = models.CharField(max_length=200, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["store", "status"], name="ct_booking_status"),
        ]

    def __str__(self) -> str:
        return f"Booking({self.service.name}, {self.customer_phone}, {self.status})"


# ---------------------------------------------------------------------------
# Story 6.3 — Quote Request → Quote
# ---------------------------------------------------------------------------


class QuoteRequest(TenantModel):
    """Customer's request for a custom job quote."""

    STATUS_OPEN = "OPEN"
    STATUS_QUOTED = "QUOTED"
    STATUS_CLOSED = "CLOSED"

    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_QUOTED, "Quoted"),
        (STATUS_CLOSED, "Closed"),
    ]

    customer_phone = models.CharField(max_length=20)
    customer_name = models.CharField(max_length=200, blank=True, default="")
    description = models.TextField()
    service = models.ForeignKey(
        Service, null=True, blank=True, on_delete=models.SET_NULL, related_name="quote_requests"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["store", "status"], name="ct_quotereq_status"),
        ]

    def __str__(self) -> str:
        return f"QuoteRequest({self.id}, {self.customer_phone}, status={self.status})"


class Quote(TenantModel):
    """Formal price quote from contractor in response to a QuoteRequest."""

    STATUS_QUOTED = "QUOTED"
    STATUS_ACCEPTED = "ACCEPTED"
    STATUS_REJECTED = "REJECTED"

    STATUS_CHOICES = [
        (STATUS_QUOTED, "Quoted"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_REJECTED, "Rejected"),
    ]

    quote_request = models.OneToOneField(
        QuoteRequest, on_delete=models.CASCADE, related_name="quote"
    )
    line_items = models.JSONField(
        help_text="List of {description, quantity, unit_price} dicts.",
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    valid_until = models.DateField()
    notes = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_QUOTED, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["store", "status"], name="idx_contracting_quote_status"),
        ]

    def __str__(self) -> str:
        return f"Quote({self.id}, status={self.status}, total={self.total_amount})"


# ---------------------------------------------------------------------------
# Story 6.4 — Job + Milestones + Completion Photos
# ---------------------------------------------------------------------------


class Job(TenantModel):
    """A job created from a confirmed booking or accepted quote."""

    STATUS_PENDING = "PENDING"
    STATUS_IN_PROGRESS = "IN_PROGRESS"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_SETTLED = "SETTLED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_SETTLED, "Settled — invoice paid"),
    ]

    VALID_TRANSITIONS: dict[str, list[str]] = {
        STATUS_PENDING: [STATUS_IN_PROGRESS],
        STATUS_IN_PROGRESS: [STATUS_COMPLETED],
        STATUS_COMPLETED: [STATUS_SETTLED],
        STATUS_SETTLED: [],
    }

    booking = models.OneToOneField(
        ServiceBooking, null=True, blank=True, on_delete=models.SET_NULL, related_name="job"
    )
    quote = models.OneToOneField(
        Quote, null=True, blank=True, on_delete=models.SET_NULL, related_name="job"
    )
    assigned_worker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_jobs",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["store", "status"], name="idx_contracting_job_status"),
        ]

    def __str__(self) -> str:
        return f"Job({self.id}, {self.title!r}, status={self.status})"

    def transition(self, new_status: str) -> None:
        """Enforce Job state machine. Raises ValueError on bad transitions."""
        allowed = self.VALID_TRANSITIONS.get(self.status, [])
        if new_status not in allowed:
            raise ValueError(
                f"Cannot transition Job from {self.status!r} to {new_status!r}."
            )
        self.status = new_status
        if new_status == self.STATUS_COMPLETED:
            self.completed_at = timezone.now()
        self.save(
            update_fields=["status", "completed_at"]
            if new_status == self.STATUS_COMPLETED
            else ["status"]
        )


class JobMilestone(TenantModel):
    """Milestone within a job. Contractor uploads completion photo when done."""

    STATUS_PENDING = "PENDING"
    STATUS_COMPLETED = "COMPLETED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_COMPLETED, "Completed"),
    ]

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="milestones")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )
    completion_photo = models.ImageField(
        upload_to="contracting/milestones/",
        null=True,
        blank=True,
        help_text="Compressed to WebP ≤ 800 KB before saving.",
    )
    notes = models.TextField(blank=True, default="")
    completed_at = models.DateTimeField(null=True, blank=True)
    position = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "created_at"]

    def __str__(self) -> str:
        return f"Milestone({self.title!r}, job={self.job_id}, status={self.status})"


# ---------------------------------------------------------------------------
# Story 6.5 — Invoice + WhatsApp-shareable PDF
# ---------------------------------------------------------------------------


def _generate_invoice_token(invoice_id: str) -> str:
    """HMAC-SHA256 signed token for the shareable invoice link."""
    secret = getattr(settings, "HMAC_QR_SECRET", "dev-secret")
    sig = hmac.new(secret.encode(), invoice_id.encode(), hashlib.sha256).hexdigest()
    return f"{invoice_id}.{sig}"


def _verify_invoice_token(token: str) -> "str | None":
    """Return invoice_id if token is valid, else None."""
    try:
        invoice_id, sig = token.rsplit(".", 1)
        secret = getattr(settings, "HMAC_QR_SECRET", "dev-secret")
        expected = hmac.new(secret.encode(), invoice_id.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(expected, sig):
            return invoice_id
    except Exception:
        pass
    return None


class Invoice(TenantModel):
    """
    Contractor invoice generated when a job is completed.

    PDF is generated by generate_invoice_pdf Celery task (WeasyPrint).
    shareable_token is HMAC-signed — safe to share via WhatsApp link.
    payment_status: UNPAID → PAID (set by payment_confirmed signal, Story 6.6).
    """

    PAYMENT_STATUS_UNPAID = "UNPAID"
    PAYMENT_STATUS_PAID = "PAID"

    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_STATUS_UNPAID, "Unpaid"),
        (PAYMENT_STATUS_PAID, "Paid"),
    ]

    job = models.OneToOneField(Job, on_delete=models.CASCADE, related_name="invoice")
    line_items = models.JSONField(
        help_text="List of {description, quantity, unit_price} dicts.",
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default=PAYMENT_STATUS_UNPAID,
        db_index=True,
    )
    pdf_file = models.FileField(
        upload_to="contracting/invoices/",
        null=True,
        blank=True,
    )
    shareable_token = models.CharField(max_length=200, blank=True, default="", db_index=True)
    payment_transaction = models.ForeignKey(
        "payment.MpesaTransaction",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="invoices",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["store", "payment_status"], name="ct_invoice_payment"
            ),
        ]

    def __str__(self) -> str:
        return f"Invoice({self.id}, job={self.job_id}, {self.payment_status})"

    def get_shareable_url(self) -> str:
        return f"/api/v1/contracting/invoices/{self.shareable_token}/download/"
