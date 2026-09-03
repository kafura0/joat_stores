"""
Store-scoped permission classes for DRF views.

IsStoreScoped    — user belongs to request.store (store_id match)
IsPlatformAdmin  — user.role == platform_admin (no store required)
IsStoreOwner     — user.role == store_owner for request.store
IsStoreManager   — user.role in (store_owner, store_manager) for request.store
HasPlanFeature   — store's plan includes the required feature

RULE: Every view must use at least one of these — never use
      rest_framework.permissions.IsAuthenticated directly on store-scoped views.

Implementation: Story 1.3 (stubs), Story 1.4 (IsPlatformAdmin stub),
                Story 1.5 (full implementation)
"""

from rest_framework.permissions import BasePermission


class HasStore(BasePermission):
    """
    Ensures request.store is resolved before the view runs.

    For views that accept unauthenticated (guest) requests — cart,
    checkout, public menu, etc. — this replaces the manual
    `getattr(request, "store", None)` + 404 pattern used throughout
    the codebase. TenantMiddleware sets request.store; if it's missing
    the store doesn't exist or wasn't resolved.
    """

    message = "Store not found."

    def has_permission(self, request, view):
        store = getattr(request, "store", None)
        if store is None:
            return False
        return True


class IsStoreScoped(BasePermission):
    """
    Verifies the authenticated user belongs to request.store.

    Platform admins (store_id=None) are allowed through — they have
    platform-wide visibility. TenantMiddleware already handles store
    resolution; this checks the user matches.
    """

    message = "You do not have access to this store."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Platform admins can access any store context
        if request.user.role == "platform_admin":
            return True

        store = getattr(request, "store", None)
        if store is None:
            # No store context (platform endpoint) — let other perms decide
            return True

        # User must belong to this store
        return request.user.store_id is not None and str(request.user.store_id) == str(
            store.id
        )


class IsPlatformAdmin(BasePermission):
    """Restricts access to platform_admin role only."""

    message = "Platform admin access required."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "platform_admin"
        )


class IsStoreOwner(BasePermission):
    """
    Restricts access to store_owner role for request.store.

    Platform admins also pass (they have full access).
    """

    message = "Store owner access required."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.role == "platform_admin":
            return True
        if request.user.role != "store_owner":
            return False

        store = getattr(request, "store", None)
        if store is None:
            return True
        return request.user.store_id is not None and str(request.user.store_id) == str(
            store.id
        )


class IsStoreManager(BasePermission):
    """
    Restricts access to store_manager or store_owner for request.store.

    Both store_owner and store_manager have operational access.
    Platform admins also pass.
    """

    message = "Store manager access required."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.role == "platform_admin":
            return True
        if request.user.role not in ("store_owner", "store_manager"):
            return False

        store = getattr(request, "store", None)
        if store is None:
            return True
        return request.user.store_id is not None and str(request.user.store_id) == str(
            store.id
        )


_FEATURE_FLAG_MAP = {
    "analytics": "has_analytics",
    "qr_codes": "has_qr_codes",
    "ai": "has_ai_features",
    "ai_features": "has_ai_features",
    "whatsapp": "has_whatsapp",
}


class HasPlanFeature(BasePermission):
    """
    Checks that the store's subscription plan includes a required feature flag.

    Usage:
        class MyView(APIView):
            permission_classes = [IsStoreScoped, HasPlanFeature]
            required_plan_feature = "analytics"   # maps to Plan.has_analytics

    Supported feature names: analytics, qr_codes, ai (or ai_features), whatsapp.
    Views without required_plan_feature are allowed through.
    """

    message = "This feature is not available on your current plan."
    code = "PLAN_FEATURE_UNAVAILABLE"

    def has_permission(self, request, view):
        feature = getattr(view, "required_plan_feature", None)
        if feature is None:
            return True

        store = getattr(request, "store", None)
        if store is None:
            return True  # Platform endpoint — no store context, allow through

        try:
            plan = store.subscription.plan
        except Exception:
            return False  # No subscription → no paid features

        if plan is None:
            return False

        flag = _FEATURE_FLAG_MAP.get(feature)
        if flag is None:
            return False  # Unknown feature name — deny (fail safe)

        return bool(getattr(plan, flag, False))


# ── Permission Matrix ────────────────────────────────────────────────────────
# Maps role → set of allowed permission codes.
# Views declare `required_permission = "code"` and HasPermission checks this matrix.

PERMISSION_MATRIX = {
    "store_owner": {
        "products.create",
        "products.edit",
        "products.delete",
        "orders.view",
        "orders.confirm",
        "orders.cancel",
        "payments.process",
        "payments.refund",
        "payments.refund.approve",
        "inventory.view",
        "inventory.adjust",
        "inventory.count",
        "staff.create",
        "staff.edit",
        "staff.deactivate",
        "settings.view",
        "settings.edit",
        "settings.financial",
        "reports.view",
        "reports.export",
        "happy_hours.create",
        "happy_hours.edit",
        "happy_hours.delete",
        "tabs.view",
        "tabs.create",
        "tabs.close",
        "menu.view",
        "menu.edit",
    },
    "store_manager": {
        "products.view",
        "orders.view",
        "orders.confirm",
        "payments.process",
        "inventory.view",
        "inventory.adjust",
        "settings.view",
        "reports.view",
        "happy_hours.create",
        "happy_hours.edit",
        "tabs.view",
        "tabs.create",
        "tabs.close",
        "menu.view",
        "menu.edit",
    },
    "cashier": {
        "products.view",
        "orders.view",
        "payments.process",
        "tabs.view",
        "tabs.close",
    },
    "waiter": {
        "products.view",
        "orders.view",
        "tabs.view",
        "tabs.create",
        "menu.view",
    },
    "kitchen": {
        "orders.view",
        "menu.view",
    },
}


class HasPermission(BasePermission):
    """
    View-level permission check against the permission matrix.

    Usage:
        class MyView(APIView):
            permission_classes = [HasPermission]
            required_permission = "products.create"

    If required_permission is not set, the view is allowed for any authenticated user.
    """

    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        required = getattr(view, "required_permission", None)
        if required is None:
            return True

        if not request.user or not request.user.is_authenticated:
            return False

        # Platform admins have all permissions
        if request.user.role == "platform_admin":
            return True

        role = request.user.role
        allowed = PERMISSION_MATRIX.get(role, set())
        return required in allowed
