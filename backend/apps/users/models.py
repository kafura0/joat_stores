"""
Custom user model for joat_stores.

User is store-scoped — the same person at Store A and Store B = two separate
User records with different store_id. Platform admins have store_id = None.

PlatformUser is the global cross-tenant identity — one record per person,
regardless of how many stores they shop at. Each store-scoped User links
back to a PlatformUser via the platform_user FK.

Story 1.5 adds JWT auth with store_id + role claims.
Story 1.4 adds the Store FK constraint.
Cross-tenant hub: PlatformUser model added 2026-06.
"""

from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(DjangoUserManager):
    """Custom manager: email as the primary identifier, not username."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        extra_fields.setdefault("role", "customer")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", "platform_admin")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class PlatformUser(models.Model):
    """
    Global cross-tenant user identity.

    One record per person, regardless of how many stores they shop at.
    This is NOT a tenant model — it has no store FK.
    Each store-scoped User record links back to this via platform_user FK.

    Hub authentication uses the password field directly on PlatformUser.
    """

    email = models.EmailField(unique=True, db_index=True)
    password = models.CharField(_("password"), max_length=128)
    phone = models.CharField(max_length=30, unique=True, null=True, blank=True)
    full_name = models.CharField(max_length=255, blank=True, default="")
    avatar_url = models.URLField(blank=True, default="")
    google_sub = models.CharField(
        max_length=255, unique=True, null=True, blank=True,
        help_text="Google OAuth subject ID for cross-store identity linking.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        verbose_name = _("Platform User")
        verbose_name_plural = _("Platform Users")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.email

    def set_password(self, raw_password: str) -> None:
        from django.contrib.auth.hashers import make_password
        self.password = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.password)

    @property
    def is_authenticated(self):
        """Duck-typing compat with DRF's IsAuthenticated permission."""
        return True


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

    platform_user = models.ForeignKey(
        PlatformUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="store_users",
        help_text="Links this store-scoped user to their global identity.",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

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
