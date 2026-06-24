"""
URL configuration for joat_stores.
API routes added per epic. All routes prefixed /api/v1/.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.analytics.urls import platform_urlpatterns as analytics_platform_urlpatterns
from apps.saas.urls import platform_urlpatterns as saas_platform_urlpatterns
from apps.store.urls import storefront_urlpatterns
from core.worker_health import WorkerHealthView


def health_check(request):
    """Minimal health check — no DB query, no auth."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health/", health_check, name="health"),
    path("health/workers/", WorkerHealthView.as_view(), name="health-workers"),  # Story 7.3
    path("admin/", admin.site.urls),
    # OpenAPI schema — Story 1.6
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-docs",
    ),
    # Domain app routes added per epic:
    path("api/v1/platform/stores/", include("apps.store.urls")),  # Story 1.4
    path("api/v1/store/", include((storefront_urlpatterns, "store-public"))),  # Story 1.7
    path("api/v1/auth/", include("apps.users.urls")),           # Story 1.5
    path("api/v1/store/", include("apps.product.urls")),      # Epic 4 — product catalog
    path("api/v1/store/", include("apps.order.urls")),        # Epic 4 — cart + checkout + orders
    path("api/v1/payments/", include("apps.payment.urls", namespace="payment")),  # Epic 2
    path("api/v1/restaurant/", include("apps.restaurant.urls")),  # Epic 3
    path("t/<uuid:table_id>/", include("apps.restaurant.fallback_urls")),  # Story 3.5 fallback
    path("p/", include("apps.product.public_urls")),  # Story 4.1 — product QR scan
    path("api/v1/bar/", include("apps.bar.urls", namespace="bar")),  # Epic 5
    path("api/v1/contracting/", include("apps.contracting.urls", namespace="contracting")),  # Epic 6
    path("api/v1/analytics/", include("apps.analytics.urls", namespace="analytics")),  # Epic 8
    path("api/v1/platform/", include((analytics_platform_urlpatterns, "platform-analytics"))),  # Epic 8 platform
    path("api/v1/saas/", include("apps.saas.urls", namespace="saas")),  # Epic 9
    path("api/v1/platform/", include((saas_platform_urlpatterns, "platform-saas"))),  # Epic 9 platform
    path("api/v1/ai/", include("apps.ai.urls", namespace="ai")),  # Epic 9.5 scaffold / Epic 11
    path("api/v1/loyalty/", include("apps.loyalty.urls", namespace="loyalty")),  # Epic 10
    path("api/v1/notifications/", include("apps.notifications.urls", namespace="notifications")),  # Epic 10
    # Customer Hub — cross-tenant portal
    path("api/v1/hub/", include("apps.customer_hub.urls")),
    # Allauth — Story 1.5
    path("accounts/", include("allauth.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
