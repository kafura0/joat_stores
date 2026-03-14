"""
Order models — Story 4.3.

Order: retail order lifecycle state machine.
CartSnapshot: PostgreSQL safety-net written before STK Push (Story 4.2/4.4).
"""

import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from core.models import TenantModel


class OrderStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    FULFILLED = "fulfilled", "Fulfilled"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


VALID_ORDER_TRANSITIONS = {
    OrderStatus.PENDING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
    OrderStatus.CONFIRMED: [OrderStatus.FULFILLED, OrderStatus.CANCELLED],
    OrderStatus.FULFILLED: [OrderStatus.COMPLETED],
    OrderStatus.COMPLETED: [],
    OrderStatus.CANCELLED: [],
}


class InvalidOrderTransition(Exception):
    def __init__(self, from_status, to_status):
        super().__init__(f"Cannot transition order from {from_status!r} to {to_status!r}")


class Order(TenantModel):
    """
    Retail store order.

    status follows a strict state machine enforced via transition_status().
    Direct field assignment to status is never used in business logic.
    """

    customer_phone = models.CharField(max_length=30)
    customer_name = models.CharField(max_length=255, blank=True, default="")
    customer_email = models.EmailField(blank=True, default="")
    # Delivery address JSON (nullable for pickup orders)
    delivery_address = models.JSONField(null=True, blank=True)
    # Denormalized line items snapshot (same pattern as DineInOrder)
    items_snapshot = models.JSONField(default=list)
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
        db_index=True,
    )
    # FK to payment transaction when paid
    payment_transaction = models.ForeignKey(
        "payment.MpesaTransaction",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orders",
    )
    # Authenticated customer (nullable for guest checkout)
    customer = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orders",
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    fulfilled_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["store", "status"], name="idx_order_store_status"),
            models.Index(fields=["store", "customer_phone"], name="idx_order_store_phone"),
        ]

    def __str__(self):
        return f"Order({self.id}, status={self.status}, total={self.total_amount})"

    def transition_status(self, new_status: str) -> None:
        """
        Enforce state machine. Raises InvalidOrderTransition on bad moves.
        Records transition timestamps.
        """
        allowed = VALID_ORDER_TRANSITIONS.get(self.status, [])
        if new_status not in allowed:
            raise InvalidOrderTransition(self.status, new_status)

        from django.utils import timezone

        self.status = new_status
        now = timezone.now()
        if new_status == OrderStatus.CONFIRMED:
            self.confirmed_at = now
        elif new_status == OrderStatus.FULFILLED:
            self.fulfilled_at = now
        elif new_status == OrderStatus.COMPLETED:
            self.completed_at = now
        elif new_status == OrderStatus.CANCELLED:
            self.cancelled_at = now

        self.save(update_fields=["status", "confirmed_at", "fulfilled_at", "completed_at", "cancelled_at"])


class CartSnapshot(TenantModel):
    """
    PostgreSQL safety-net for cart state written before STK Push initiation.

    Story 4.2/4.4: If Redis fails between cart add and payment initiation,
    the checkout view writes the cart to this table before calling initiate_payment().
    On payment recovery (Story 4.8), the order is reconstructed from this snapshot.
    """

    # Session key (anonymous cart) or user ID (authenticated cart)
    cart_key = models.CharField(max_length=255, db_index=True)
    items = models.JSONField(default=list)
    linked_order = models.OneToOneField(
        Order,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cart_snapshot",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["store", "cart_key"], name="idx_cartsnapshot_key"),
        ]
