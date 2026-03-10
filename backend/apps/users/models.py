"""
Custom user model for joat_stores.

User is store-scoped — the same person at Store A and Store B = two separate
User records with different store_id. Platform admins have store_id = None.

Story 1.5 adds JWT auth with store_id + role claims.
Story 1.4 adds the Store FK constraint.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Custom user model for joat_stores.

    Roles (enforced via JWT claim, not Django permissions):
        - platform_admin: no store_id, platform-wide access
        - store_owner: owns a store, full store access
        - store_manager: manages a store, limited store access
        - customer: store-scoped customer account

    RULE: Never use is_staff/is_superuser for RBAC — JWT role claim only.
    RULE: Never filter by email without store_id — same email = different
          customers at different stores.
    """

    class Role(models.TextChoices):
        PLATFORM_ADMIN = "platform_admin", _("Platform Admin")
        STORE_OWNER = "store_owner", _("Store Owner")
        STORE_MANAGER = "store_manager", _("Store Manager")
        CUSTOMER = "customer", _("Customer")

    # Email as username (no separate username field)
    username = None  # type: ignore[assignment]
    # unique per store, not globally — compound constraint added in Story 1.2
    email = models.EmailField(_("email address"), unique=False)

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER,
    )

    store = models.ForeignKey(
        "store.Store",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="users",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        constraints = [
            models.UniqueConstraint(
                fields=["email", "store"],
                name="uq_user_email_store",
            ),
            # PostgreSQL treats NULLs as distinct in unique constraints, so
            # uq_user_email_store does NOT prevent duplicate platform_admin emails
            # (store=NULL). This partial index fills that gap.
            models.UniqueConstraint(
                fields=["email"],
                condition=models.Q(store__isnull=True),
                name="uq_platform_admin_email",
            ),
        ]

    def __str__(self) -> str:
        return self.email
