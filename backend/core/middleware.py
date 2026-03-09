"""
TenantMiddleware

Resolves request.store from:
  1. Path bypass — /health/, /admin/, etc. skip resolution entirely
  2. Platform subdomain bypass — admin.joat.com, api.joat.com skip resolution
  3. X-Store-ID header — UUID lookup by Store.id
  4. Host header — domain lookup by Store.domain

Sets request.store before any view logic runs.
Returns HTTP 404 if no matching store found.
Returns HTTP 503 if store.status == 'suspended'.

Platform subdomains: controlled via settings.PLATFORM_SUBDOMAINS
Bypass paths: controlled via settings.MIDDLEWARE_BYPASS_PATHS

Implementation: Story 1.2
"""

import uuid

from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin


class TenantMiddleware(MiddlewareMixin):
    """
    Resolves request.store before any view logic runs.

    Resolution order:
      1. Path bypass → request.store = None, pass through
      2. Platform subdomain bypass → request.store = None, pass through
      3. X-Store-ID header → lookup by UUID
      4. Host header → lookup by domain
      5. Not found → 404
      6. Suspended → 503
      7. Set request.store = store, pass through
    """

    def process_request(self, request):
        # lazy import — avoids import at module load time
        from apps.store.models import Store, StoreStatus

        path = request.path_info
        host = request.get_host().split(":")[0].lower()

        # 1. Path bypass — health check, Django admin, OpenAPI schema, etc.
        bypass_paths = getattr(
            settings,
            "MIDDLEWARE_BYPASS_PATHS",
            ["/health/", "/admin/"],
        )
        if any(path.startswith(bp) for bp in bypass_paths):
            request.store = None
            return None

        # 2. Platform subdomain bypass — admin panel, API subdomain, localhost
        platform_subdomains = getattr(settings, "PLATFORM_SUBDOMAINS", [])
        if host in platform_subdomains:
            request.store = None
            return None

        store = None

        # 3. X-Store-ID header lookup (UUID)
        store_id_header = request.headers.get("X-Store-ID")
        if store_id_header:
            try:
                store_uuid = uuid.UUID(store_id_header)
                store = Store.objects.filter(id=store_uuid).first()
            except ValueError:
                pass  # Invalid UUID — fall through to domain lookup

        # 4. Host header domain lookup
        if store is None:
            store = Store.objects.filter(domain=host).first()

        # 5. Not found → 404
        if store is None:
            return JsonResponse(
                {
                    "errors": [
                        {
                            "field": None,
                            "message": "Store not found.",
                            "code": "NOT_FOUND",
                        }
                    ]
                },
                status=404,
            )

        # 6. Suspended → 503
        if store.status == StoreStatus.SUSPENDED:
            return JsonResponse(
                {
                    "errors": [
                        {
                            "field": None,
                            "message": "Store is suspended.",
                            "code": "STORE_SUSPENDED",
                        }
                    ]
                },
                status=503,
            )

        # 7. Set store on request
        request.store = store
        return None
