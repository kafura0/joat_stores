"""
Store-scoped permission classes for DRF views.

IsStoreScoped    — request.user is authenticated AND belongs to request.store
IsPlatformAdmin  — request.user has role=platform_admin (cross-store access)
IsStoreOwner     — request.user has role=store_owner for request.store
IsStoreManager   — request.user has role=store_manager for request.store

RULE: Every view must use at least one of these — never use
      rest_framework.permissions.IsAuthenticated directly on store-scoped views.

Implementation: Story 1.5
"""

# TODO: Story 1.5 — implement all permission classes
