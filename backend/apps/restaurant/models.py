"""
Restaurant domain models.

Story 3.1: MenuSection, MenuItem, ModifierGroup, Modifier
Story 3.3: Table
Story 3.4: TableSession
Story 3.6: DineInOrder, KitchenTicket
Story 3.7: PendingOrder
Story 3.9: Reservation

All models inherit TenantModel (UUID PK, store FK, soft-delete, TenantQuerySet).
"""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from core.models import TenantModel


class MenuSection(TenantModel):
    """Ordered grouping of MenuItems within a store's menu."""

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    position = models.PositiveSmallIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ["position", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["store", "name"],
                name="uq_restaurant_menusection_store_name",
            )
        ]
        indexes = [
            models.Index(
                fields=["store", "position"],
                name="idx_rst_msection_store_pos",
            )
        ]

    def __str__(self) -> str:
        return self.name


class MenuItem(TenantModel):
    """Individual dish with price, allergen flag, and time-based availability."""

    section = models.ForeignKey(
        MenuSection,
        on_delete=models.CASCADE,
        related_name="items",
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default="")
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    contains_allergens = models.BooleanField(default=False)
    allergen_description = models.TextField(blank=True, default="")
    is_available = models.BooleanField(default=True)

    # Time-based scheduling — null means always available
    available_from = models.TimeField(
        null=True,
        blank=True,
        help_text="Start time for availability window (e.g. 06:00). Null = always.",
    )
    available_until = models.TimeField(
        null=True,
        blank=True,
        help_text="End time for availability window (e.g. 11:00). Null = always.",
    )

    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "name"]
        indexes = [
            models.Index(
                fields=["store", "section"],
                name="idx_rst_mitem_store_section",
            ),
            models.Index(
                fields=["store", "is_available"],
                name="idx_rst_mitem_store_avail",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def is_available_now(self, current_time=None) -> bool:
        """Return True if the item is available at current_time (or right now)."""
        if not self.is_available:
            return False
        if self.available_from is None and self.available_until is None:
            return True
        if current_time is None:
            from django.utils import timezone

            current_time = timezone.localtime().time()
        if self.available_from and self.available_until:
            return self.available_from <= current_time <= self.available_until
        if self.available_from:
            return current_time >= self.available_from
        if self.available_until:
            return current_time <= self.available_until
        return True


class ModifierGroup(TenantModel):
    """A set of options for a MenuItem (e.g. "Choose sauce")."""

    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name="modifier_groups",
    )
    name = models.CharField(max_length=100)
    min_selections = models.PositiveSmallIntegerField(
        default=0,
        help_text="Minimum number of modifiers the customer must choose.",
    )
    max_selections = models.PositiveSmallIntegerField(
        default=1,
        help_text="Maximum number of modifiers the customer may choose.",
    )
    is_required = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(
                fields=["store", "menu_item"],
                name="idx_rst_modgrp_store_item",
            )
        ]

    def __str__(self) -> str:
        return f"{self.menu_item.name} — {self.name}"


class Modifier(TenantModel):
    """Individual option within a ModifierGroup, with optional price addition."""

    modifier_group = models.ForeignKey(
        ModifierGroup,
        on_delete=models.CASCADE,
        related_name="modifiers",
    )
    name = models.CharField(max_length=100)
    price_addition = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default="0.00",
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Additional cost when this modifier is selected.",
    )
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(
                fields=["store", "modifier_group"],
                name="idx_rst_modifier_store_grp",
            )
        ]

    def __str__(self) -> str:
        return self.name


class Table(TenantModel):
    """Physical table in a restaurant. QR codes link to a specific table."""

    number = models.PositiveSmallIntegerField(
        help_text="Table number visible to staff/customers.",
    )
    name = models.CharField(
        max_length=50, blank=True, default="",
        help_text="Optional friendly name (e.g. 'Window Table').",
    )
    capacity = models.PositiveSmallIntegerField(default=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["number"]
        constraints = [
            models.UniqueConstraint(
                fields=["store", "number"],
                name="uq_restaurant_table_store_number",
            )
        ]
        indexes = [
            models.Index(
                fields=["store", "is_active"],
                name="idx_rst_table_store_active",
            )
        ]

    def __str__(self) -> str:
        return f"Table {self.number}"


class InvalidSessionTransition(Exception):
    """Raised when a TableSession state transition is not allowed."""

    def __init__(self, current: str, attempted: str) -> None:
        self.current = current
        self.attempted = attempted
        super().__init__(
            f"Cannot transition TableSession from {current!r} to {attempted!r}."
        )


class TableSession(TenantModel):
    """
    A dining session at a table — created when a customer scans the QR code.

    State machine (enforced via .transition() — never direct field assignment):
        OPEN → BILL_REQUESTED → CLOSED

    UniqueConstraint ensures at most one OPEN session exists per table at any time.
    """

    STATUS_OPEN = "OPEN"
    STATUS_BILL_REQUESTED = "BILL_REQUESTED"
    STATUS_CLOSED = "CLOSED"

    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_BILL_REQUESTED, "Bill Requested"),
        (STATUS_CLOSED, "Closed"),
    ]

    # Valid next states for each current state
    VALID_TRANSITIONS: dict[str, list[str]] = {
        STATUS_OPEN: [STATUS_BILL_REQUESTED],
        STATUS_BILL_REQUESTED: [STATUS_CLOSED],
        STATUS_CLOSED: [],
    }

    table = models.ForeignKey(
        Table,
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_OPEN,
        db_index=True,
    )
    assigned_waiter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Waiter assigned to this session; name appears on kitchen tickets.",
    )
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-opened_at"]
        constraints = [
            # At most one OPEN session per table — DB-level enforcement.
            models.UniqueConstraint(
                fields=["table"],
                condition=models.Q(status="OPEN"),
                name="uq_restaurant_tablesession_one_open_per_table",
            )
        ]
        indexes = [
            models.Index(
                fields=["store", "status"],
                name="idx_rst_tablesession_store_status",
            ),
            models.Index(
                fields=["table", "status"],
                name="idx_rst_tablesession_table_status",
            ),
        ]

    def __str__(self) -> str:
        return f"Session(table={self.table.number}, status={self.status})"

    def transition(self, new_status: str) -> None:
        """
        Enforce the state machine. Never assign self.status directly.

        Raises InvalidSessionTransition if the transition is not allowed.
        """
        allowed = self.VALID_TRANSITIONS.get(self.status, [])
        if new_status not in allowed:
            raise InvalidSessionTransition(self.status, new_status)

        self.status = new_status
        if new_status == self.STATUS_CLOSED:
            from django.utils import timezone

            self.closed_at = timezone.now()
        self.save(update_fields=["status", "closed_at"] if new_status == self.STATUS_CLOSED else ["status"])


# ---------------------------------------------------------------------------
# Story 3.6 — DineInOrder + KitchenTicket
# ---------------------------------------------------------------------------


class DineInOrder(TenantModel):
    """
    Customer's dine-in order linked to a TableSession.

    items_snapshot is a denormalized JSON list built at creation time —
    it never changes even if the menu is edited afterwards.

    Snapshot item format:
    {
        "menu_item_id": "<uuid>",
        "name": "Nyama Choma",
        "price": "850.00",
        "quantity": 2,
        "contains_allergens": false,
        "modifiers": [
            {"modifier_id": "<uuid>", "name": "Extra Sauce", "price_addition": "50.00"}
        ]
    }
    """

    STATUS_PENDING = "PENDING"
    STATUS_CONFIRMED = "CONFIRMED"
    STATUS_READY = "READY"
    STATUS_CANCELLED = "CANCELLED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_CONFIRMED, "Confirmed by kitchen"),
        (STATUS_READY, "Ready for service"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    session = models.ForeignKey(
        TableSession,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    items_snapshot = models.JSONField(
        help_text="Denormalized list of ordered items captured at creation time.",
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    placed_at = models.DateTimeField(auto_now_add=True)
    # Linked on conversion from PendingOrder (Story 3.8) or after payment confirmation
    payment_transaction = models.ForeignKey(
        "payment.MpesaTransaction",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dine_in_orders",
        help_text="M-Pesa transaction linked to this order (advance or table-side payment).",
    )

    class Meta:
        ordering = ["-placed_at"]
        indexes = [
            models.Index(
                fields=["store", "status"],
                name="idx_rst_dineinorder_store_status",
            ),
            models.Index(
                fields=["session"],
                name="idx_rst_dineinorder_session",
            ),
        ]

    def __str__(self) -> str:
        return f"DineInOrder({self.id}, session={self.session_id}, status={self.status})"


class KitchenTicket(TenantModel):
    """
    Denormalized kitchen display ticket created alongside a DineInOrder.

    All item, modifier, and waiter data is baked in at creation — the kitchen
    display query requires no joins beyond the single KitchenTicket table.

    Status lifecycle: PENDING → IN_PROGRESS → COMPLETED | CANCELLED
    """

    STATUS_PENDING = "PENDING"
    STATUS_IN_PROGRESS = "IN_PROGRESS"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_CANCELLED = "CANCELLED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    VALID_TRANSITIONS: dict[str, list[str]] = {
        STATUS_PENDING: [STATUS_IN_PROGRESS, STATUS_CANCELLED],
        STATUS_IN_PROGRESS: [STATUS_COMPLETED, STATUS_CANCELLED],
        STATUS_COMPLETED: [],
        STATUS_CANCELLED: [],
    }

    order = models.OneToOneField(
        DineInOrder,
        on_delete=models.CASCADE,
        related_name="ticket",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    # Denormalized fields — copied once at creation, never updated
    items_snapshot = models.JSONField(
        help_text="Copy of DineInOrder.items_snapshot at ticket creation time.",
    )
    waiter_name = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Denormalized waiter name from session.assigned_waiter at creation time.",
    )
    table_number = models.PositiveSmallIntegerField(
        help_text="Denormalized table number at creation time.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["store", "status"],
                name="idx_rst_kitchenticket_store_status",
            ),
        ]

    def __str__(self) -> str:
        return f"KitchenTicket({self.id}, table={self.table_number}, status={self.status})"

    def transition(self, new_status: str) -> None:
        """Enforce KitchenTicket state machine. Raises InvalidSessionTransition on bad moves."""
        allowed = self.VALID_TRANSITIONS.get(self.status, [])
        if new_status not in allowed:
            raise InvalidSessionTransition(self.status, new_status)
        self.status = new_status
        self.save(update_fields=["status"])


# ---------------------------------------------------------------------------
# Story 3.7 — PendingOrder
# ---------------------------------------------------------------------------


def _generate_pin() -> str:
    """Generate a random 6-digit PIN string."""
    import random

    return f"{random.randint(0, 999999):06d}"


class PendingOrder(TenantModel):
    """
    Pre-arrival order created by a customer who browses the public menu and
    pre-selects items before arriving at the restaurant.

    The customer receives a 6-digit PIN to give the waiter on arrival.
    The waiter looks up the PendingOrder by PIN or phone, then converts it to
    a DineInOrder linked to an active TableSession.

    Lifecycle: PENDING → CONVERTED | EXPIRED
    PAID is set by Story 3.8 (advance M-Pesa payment) — stored here so the
    conversion path is consistent regardless of payment state.
    """

    STATUS_PENDING = "PENDING"
    STATUS_PAID = "PAID"
    STATUS_CONVERTED = "CONVERTED"
    STATUS_EXPIRED = "EXPIRED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid in advance"),
        (STATUS_CONVERTED, "Converted to dine-in"),
        (STATUS_EXPIRED, "Expired"),
    ]

    phone = models.CharField(
        max_length=20,
        help_text="Customer phone number in E.164 format.",
    )
    pin = models.CharField(
        max_length=6,
        default=_generate_pin,
        help_text="6-digit PIN the customer gives the waiter on arrival.",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    items_snapshot = models.JSONField(
        help_text="Denormalized list of ordered items captured at creation time.",
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    expires_at = models.DateTimeField(
        help_text="24h from creation — after this the order is purged by Celery beat.",
    )
    # Populated on conversion
    converted_order = models.OneToOneField(
        DineInOrder,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pending_order",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["store", "status"],
                name="idx_rst_pendingorder_store_status",
            ),
            models.Index(
                fields=["store", "pin", "status"],
                name="idx_rst_pendingorder_store_pin_status",
            ),
            models.Index(
                fields=["store", "phone", "status"],
                name="idx_rst_pendingorder_store_phone_status",
            ),
        ]

    def __str__(self) -> str:
        return f"PendingOrder({self.id}, pin={self.pin}, status={self.status})"


# ---------------------------------------------------------------------------
# Story 3.9 — Reservation
# ---------------------------------------------------------------------------


class Reservation(TenantModel):
    """
    Table reservation: customer books a time slot + party size, receives confirmation.

    State machine (via .transition()):
        PENDING → CONFIRMED → SEATED | NO_SHOW

    On SEATED, a TableSession is auto-created for the reserved table.
    """

    STATUS_PENDING = "PENDING"
    STATUS_CONFIRMED = "CONFIRMED"
    STATUS_SEATED = "SEATED"
    STATUS_NO_SHOW = "NO_SHOW"
    STATUS_CANCELLED = "CANCELLED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_SEATED, "Seated"),
        (STATUS_NO_SHOW, "No Show"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    VALID_TRANSITIONS: dict[str, list[str]] = {
        STATUS_PENDING: [STATUS_CONFIRMED, STATUS_CANCELLED],
        STATUS_CONFIRMED: [STATUS_SEATED, STATUS_NO_SHOW, STATUS_CANCELLED],
        STATUS_SEATED: [],
        STATUS_NO_SHOW: [],
        STATUS_CANCELLED: [],
    }

    customer_phone = models.CharField(max_length=20)
    customer_name = models.CharField(max_length=200, blank=True, default="")
    table = models.ForeignKey(
        Table,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reservations",
        help_text="Specific table reserved. May be assigned at confirmation.",
    )
    party_size = models.PositiveSmallIntegerField()
    reserved_for = models.DateTimeField(
        help_text="Requested time slot for the reservation.",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    notes = models.TextField(blank=True, default="")
    # Auto-linked when status transitions to SEATED
    session = models.OneToOneField(
        TableSession,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reservation",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["reserved_for"]
        indexes = [
            models.Index(
                fields=["store", "status"],
                name="idx_rst_reservation_store_status",
            ),
            models.Index(
                fields=["store", "reserved_for"],
                name="idx_rst_reservation_store_time",
            ),
        ]

    def __str__(self) -> str:
        return f"Reservation({self.id}, phone={self.customer_phone}, status={self.status}, for={self.reserved_for})"

    def transition(self, new_status: str) -> None:
        """Enforce state machine. Raises InvalidSessionTransition on bad moves."""
        allowed = self.VALID_TRANSITIONS.get(self.status, [])
        if new_status not in allowed:
            raise InvalidSessionTransition(self.status, new_status)
        self.status = new_status
        self.save(update_fields=["status"])
