"""
Analytics models.

AdminPIIAccessLog — append-only audit log for Kenya DPA 2019 compliance.
                    Story 1.6 creates this; Story 12.3 enforces INSERT-only DB role.

Pre-aggregated summary models (DailyRevenueSummary, HourlyOrderSummary) added in Epic 8.

Implementation: Story 1.6
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


class AdminPIIAccessLog(models.Model):
    """
    Append-only audit log for admin access to customer PII.

    Kenya DPA 2019 requires a full audit trail of all PII access.
    The DB role should have INSERT-only privileges on this table
    (enforced in Story 12.3).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
    )
    store = models.ForeignKey(
        "store.Store",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    record_type = models.CharField(
        max_length=100,
        help_text="Model name of the accessed record.",
    )
    record_id = models.CharField(
        max_length=255,
        help_text="PK of the accessed record.",
    )
    accessed_at = models.DateTimeField(default=timezone.now, db_index=True)
    path = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Request path that triggered PII access.",
    )
    method = models.CharField(
        max_length=10,
        blank=True,
        default="",
    )

    class Meta:
        db_table = "analytics_adminpiiaccesslog"
        ordering = ["-accessed_at"]
        indexes = [
            models.Index(fields=["user", "accessed_at"]),
            models.Index(fields=["store", "accessed_at"]),
        ]

    def __str__(self):
        return (
            f"PII access: {self.user} -> {self.record_type}"
            f"#{self.record_id} at {self.accessed_at}"
        )
