"""
Store-scoped permission classes for DRF views.

IsStoreScoped    — STUB (Story 1.3): allows all requests.
                   Story 1.5 adds: request.user.store_id == request.store.id
IsPlatformAdmin  — STUB (Story 1.4): allows all authenticated requests.
                   Story 1.5 adds: request.user.role == "platform_admin"
IsStoreOwner     — Story 1.5: request.user has role=store_owner for request.store
IsStoreManager   — Story 1.5: request.user has role=store_manager for request.store

RULE: Every view must use at least one of these — never use
      rest_framework.permissions.IsAuthenticated directly on store-scoped views.

Implementation: Story 1.3 (IsStoreScoped stub), Story 1.4 (IsPlatformAdmin stub),
                Story 1.5 (full implementation)
"""

from rest_framework.permissions import BasePermission


class IsStoreScoped(BasePermission):
    """
    Verifies the authenticated user belongs to request.store.

    Story 1.3 STUB — allows all requests so TenantViewSet is usable now.
    Story 1.5 replaces this body with JWT claim check:
        return (
            request.user.is_authenticated
            and str(request.user.store_id) == str(request.store.id)
        )
    """

    def has_permission(self, request, view):
        # TODO: Story 1.5 — check request.user.store_id == request.store.id
        return True  # stub: allow all for now


class IsPlatformAdmin(BasePermission):
    """
    Restricts access to platform admin users only.

    Story 1.4 STUB — allows all authenticated requests.
    Story 1.5 replaces with: request.user.role == "platform_admin"
    """

    def has_permission(self, request, view):
        # TODO: Story 1.5 — check request.user.role == "platform_admin"
        return request.user and request.user.is_authenticated
