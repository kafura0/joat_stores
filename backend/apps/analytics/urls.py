"""
Analytics URL configuration.

Stories 8.2-8.7.
All analytics endpoints read from pre-aggregated models — never live queries.
"""

from django.urls import path

from apps.analytics.views import (
    AIEventListView,
    BarOccupancyView,
    BarTabMetricsView,
    DailyRevenueSummaryCSVExport,
    PlatformGMVView,
    PlatformUnitEconomicsView,
    RestaurantPeakHoursView,
    RestaurantTableTurnRateView,
    StoreSummaryView,
    StoreFirstOrderView,
    TenantHealthListView,
)

app_name = "analytics"

urlpatterns = [
    # Story 8.3 — Per-store summary
    path("summary/", StoreSummaryView.as_view(), name="store-summary"),
    # Story 8.2 — AIEvent list (platform admin)
    path("events/", AIEventListView.as_view(), name="ai-events"),
    # Story 8.4 — Restaurant analytics
    path("restaurant/peak-hours/", RestaurantPeakHoursView.as_view(), name="restaurant-peak-hours"),
    path(
        "restaurant/table-turn-rate/",
        RestaurantTableTurnRateView.as_view(),
        name="restaurant-table-turn-rate",
    ),
    # Story 8.5 — Bar analytics
    path("bar/tab-metrics/", BarTabMetricsView.as_view(), name="bar-tab-metrics"),
    path("bar/occupancy/", BarOccupancyView.as_view(), name="bar-occupancy"),
    # Story 12.6 — CSV export
    path("export/csv/", DailyRevenueSummaryCSVExport.as_view(), name="export-csv"),
]

# Platform analytics (registered under /api/v1/platform/ prefix in config/urls.py)
platform_urlpatterns = [
    path("analytics/gmv/", PlatformGMVView.as_view(), name="platform-gmv"),
    path(
        "analytics/unit-economics/",
        PlatformUnitEconomicsView.as_view(),
        name="platform-unit-economics",
    ),
    path(
        "analytics/tenant-health/",
        TenantHealthListView.as_view(),
        name="platform-tenant-health",
    ),
    path(
        "stores/<uuid:store_id>/first-order/",
        StoreFirstOrderView.as_view(),
        name="store-first-order",
    ),
]
