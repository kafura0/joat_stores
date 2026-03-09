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


class HasPlanFeature(BasePermission):
    """
    Checks that the store's plan includes a required feature.

    Usage:
        class MyView(TenantViewSet):
            permission_classes = [IsStoreScoped, HasPlanFeature]
            required_plan_feature = "analytics"

    Story 1.5 stub — always allows. Epic 9 adds feature flags to Plan.
    """

    message = "This feature is not available on your current plan."
    code = "PLAN_FEATURE_UNAVAILABLE"

    def has_permission(self, request, view):
        # Stub: always allow until Epic 9 adds plan feature flags
        # Epic 9 will check:
        #   feature = getattr(view, "required_plan_feature", None)
        #   plan = request.store.subscription.plan
        #   return feature in plan.features
        return True
