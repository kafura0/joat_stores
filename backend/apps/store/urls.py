"""
Store app URL configuration.

Platform admin endpoints:
  POST   /api/v1/platform/stores/              — provision new store
  GET    /api/v1/platform/stores/list/         — list all stores
  PATCH  /api/v1/platform/stores/{id}/status/  — update store status

Implementation: Story 1.4
"""

from django.urls import path

from apps.store.views import (
    StoreListView,
    StoreProvisionView,
    StoreStatusUpdateView,
)

app_name = "store"

urlpatterns = [
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
