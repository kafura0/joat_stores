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
    BrandingView,
    StoreListView,
    StoreProvisionView,
    StoreStatusUpdateView,
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
]

# Default urlpatterns = platform routes (config/urls.py includes both explicitly)
urlpatterns = platform_urlpatterns
