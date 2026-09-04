"""
Store app URL configuration.

Platform admin endpoints (mounted at /api/v1/platform/stores/):
  POST   /api/v1/platform/stores/              — provision new store
  GET    /api/v1/platform/stores/list/         — list all stores
  PATCH  /api/v1/platform/stores/{id}/status/  — update store status

Public storefront endpoints (mounted at /api/v1/store/):
  GET    /api/v1/store/branding/               — tenant branding (Story 1.7)

Implementation: Story 1.4, Story 1.7
"""

from django.urls import path

from apps.store.views import (
    ApplyPresetView,
    BrandingView,
    OfflineInventorySnapshotView,
    PresetListView,
    StoreListView,
    StoreLogoUploadView,
    StoreProvisionView,
    StoreSettingsView,
    StoreStatusUpdateView,
    ThemeDetailView,
)

app_name = "store"

# Platform admin routes (mounted at /api/v1/platform/stores/)
platform_urlpatterns = [
    path(
        "",
        StoreProvisionView.as_view(),
        name="store-provision",
    ),
    path(
        "list/",
        StoreListView.as_view(),
        name="store-list",
    ),
    path(
        "<uuid:pk>/status/",
        StoreStatusUpdateView.as_view(),
        name="store-status",
    ),
]

# Public storefront routes (mounted at /api/v1/store/)
storefront_urlpatterns = [
    path(
        "branding/",
        BrandingView.as_view(),
        name="store-branding",
    ),
    # Story 12.5 — PWA offline inventory snapshot for service worker background sync
    path(
        "offline-snapshot/",
        OfflineInventorySnapshotView.as_view(),
        name="offline-snapshot",
    ),
    # Phase 1-3 — Theme API (design tokens, presets, custom CSS)
    path(
        "themes/",
        ThemeDetailView.as_view(),
        name="theme-detail",
    ),
    path(
        "themes/presets/",
        PresetListView.as_view(),
        name="theme-presets",
    ),
    path(
        "themes/apply-preset/",
        ApplyPresetView.as_view(),
        name="theme-apply-preset",
    ),
    # Store settings (Story 6.1)
    path(
        "settings/",
        StoreSettingsView.as_view(),
        name="store-settings",
    ),
    path(
        "settings/logo/",
        StoreLogoUploadView.as_view(),
        name="store-logo-upload",
    ),
]

# Default urlpatterns = platform routes (config/urls.py includes both explicitly)
urlpatterns = platform_urlpatterns
