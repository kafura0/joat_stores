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


def health_check(request):
    """Minimal health check — no DB query, no auth."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health/", health_check, name="health"),
    path("admin/", admin.site.urls),
    # OpenAPI schema — Story 1.6
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-docs",
    ),
    # Domain app routes added per epic:
    # path("api/v1/stores/", include("apps.store.urls")),      # Story 1.4
    # path("api/v1/auth/", include("apps.users.urls")),        # Story 1.5
    # path("api/v1/products/", include("apps.product.urls")),  # Epic 4
    # path("api/v1/orders/", include("apps.order.urls")),      # Epic 4
    # path("api/v1/payments/", include("apps.payment.urls")),  # Epic 2
    # path("api/v1/restaurant/", include("apps.restaurant.urls")),  # Epic 3
    # path("api/v1/bar/", include("apps.bar.urls")),           # Epic 5
    # path("api/v1/analytics/", include("apps.analytics.urls")),    # Epic 8
    # path("api/v1/ai/", include("apps.ai.urls")),             # Epic 11
    # path("api/v1/loyalty/", include("apps.loyalty.urls")),   # Epic 10
    # path("api/v1/saas/", include("apps.saas.urls")),         # Epic 9
    # Allauth — Story 1.5
    path("accounts/", include("allauth.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
