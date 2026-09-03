"""
SaaS URL patterns — Epic 9.
"""

from django.urls import path

from apps.saas.platform_metrics import PlatformMetricsView
from apps.saas.views import (
    PlanDetailView,
    PlanListView,
    PlatformSubscriptionDetailView,
    PlatformSubscriptionListView,
    SubscriptionRenewView,
    SubscriptionView,
)

app_name = "saas"

urlpatterns = [
    # Plans (public + platform admin)
    path("plans/", PlanListView.as_view(), name="plan-list"),
    path("plans/<int:pk>/", PlanDetailView.as_view(), name="plan-detail"),
    # Store owner subscription
    path("subscription/", SubscriptionView.as_view(), name="subscription"),
    path("subscription/renew/", SubscriptionRenewView.as_view(), name="subscription-renew"),
]

# Mounted at /api/v1/platform/ in config/urls.py
platform_urlpatterns = [
    path("metrics/", PlatformMetricsView.as_view(), name="platform-metrics"),
    path("subscriptions/", PlatformSubscriptionListView.as_view(), name="platform-subscription-list"),
    path("subscriptions/<int:pk>/", PlatformSubscriptionDetailView.as_view(), name="platform-subscription-detail"),
]
