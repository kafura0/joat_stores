"""
Bar URL configuration.

Implementation: Stories 5.1-5.5
"""

from django.urls import path

from apps.bar.views import (
    AddRoundView,
    HappyHourListView,
    RemoveTabItemView,
    RequestBillView,
    SplitTabView,
    TabDetailView,
    TabListView,
)

app_name = "bar"

urlpatterns = [
    # Story 5.1 — Tab lifecycle
    path("tabs/", TabListView.as_view(), name="tab-list"),
    path("tabs/<uuid:tab_id>/", TabDetailView.as_view(), name="tab-detail"),
    # Story 5.2 — Round ordering + item removal
    path("tabs/<uuid:tab_id>/rounds/", AddRoundView.as_view(), name="add-round"),
    path(
        "tabs/<uuid:tab_id>/items/<uuid:item_id>/",
        RemoveTabItemView.as_view(),
        name="remove-item",
    ),
    # Story 5.5 — Bill + split settlement
    path(
        "tabs/<uuid:tab_id>/request-bill/",
        RequestBillView.as_view(),
        name="request-bill",
    ),
    path("tabs/<uuid:tab_id>/split/", SplitTabView.as_view(), name="split-tab"),
    # Story 5.4 — Happy hour management
    path("happy-hours/", HappyHourListView.as_view(), name="happy-hours"),
]
