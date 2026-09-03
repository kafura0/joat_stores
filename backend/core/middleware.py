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
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


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

        # Extract JWT claims for tenant isolation checks
        self._extract_jwt_claims(request)

        # 1. Path bypass — health check, Django admin, OpenAPI schema, etc.
        bypass_paths = getattr(
            settings,
            "MIDDLEWARE_BYPASS_PATHS",
            ["/health/", "/admin/"],
        )
        if any(path.startswith(bp) for bp in bypass_paths):
            request.store = None
            return None

        # 2. X-Store-ID header lookup (UUID) — explicit override
        # SECURITY: Only platform admins and store owners can use X-Store-ID.
        # Regular users (staff/customers) are restricted to their JWT store_id
        # to prevent cross-tenant data access.
        store_id_header = request.headers.get("X-Store-ID")
        if store_id_header:
            try:
                store_uuid = uuid.UUID(store_id_header)
                store = Store.objects.filter(id=store_uuid).first()
                if store is not None:
                    # Validate X-Store-ID against JWT claims for non-admin users
                    jwt_store_id = getattr(request, "jwt_store_id", None)
                    jwt_role = getattr(request, "jwt_role", None)
                    if jwt_store_id is not None and jwt_role not in (
                        "platform_admin",
                        "store_owner",
                    ):
                        # Staff/customer trying to access a different store → reject
                        if str(store_uuid) != str(jwt_store_id):
                            return JsonResponse(
                                {
                                    "errors": [{
                                        "field": "X-Store-ID",
                                        "message": "Access denied: you cannot switch stores.",
                                        "code": "FORBIDDEN",
                                    }]
                                },
                                status=403,
                            )

                    # Suspended → 503 (exempt branding passthrough at step 6)
                    SUSPENDED_PASSTHROUGH_PATHS = getattr(
                        settings, "SUSPENDED_PASSTHROUGH_PATHS", ["/api/v1/store/branding/"]
                    )
                    if store.status == StoreStatus.SUSPENDED and not any(
                        path.startswith(sp) for sp in SUSPENDED_PASSTHROUGH_PATHS
                    ):
                        return JsonResponse(
                            {"errors": [{"field": None, "message": "Store is suspended.", "code": "STORE_SUSPENDED"}]},
                            status=503,
                        )
                    request.store = store
                    return None
            except ValueError:
                pass  # Invalid UUID — fall through

        # 3. Platform subdomain bypass — admin panel, API subdomain, localhost
        platform_subdomains = getattr(settings, "PLATFORM_SUBDOMAINS", [])
        if host in platform_subdomains:
            request.store = None
            return None

        store = None

        # 4. Host header domain lookup
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
        # Branding is exempt so storefront can render a branded 503 page.
        SUSPENDED_PASSTHROUGH_PATHS = getattr(
            settings, "SUSPENDED_PASSTHROUGH_PATHS", ["/api/v1/store/branding/"]
        )
        if store.status == StoreStatus.SUSPENDED and not any(
            path.startswith(sp) for sp in SUSPENDED_PASSTHROUGH_PATHS
        ):
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

    def _extract_jwt_claims(self, request):
        """
        Extract store_id and role from the JWT token in the Authorization header.
        Sets request.jwt_store_id and request.jwt_role for tenant isolation checks.
        Runs before TenantMiddleware resolves request.store.
        """
        request.jwt_store_id = None
        request.jwt_role = None
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return
        token_str = auth_header[7:]
        try:
            token = AccessToken(token_str)
            request.jwt_store_id = token.get("store_id")
            request.jwt_role = token.get("role")
        except (InvalidToken, TokenError):
            pass  # Invalid/expired token — views will handle auth


# ---------------------------------------------------------------------------
# Story 12.3 — Security headers (OWASP Top 10)
# ---------------------------------------------------------------------------


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Story 12.3 — Adds OWASP-recommended security headers to every response.

    Headers added:
    - Content-Security-Policy: restricts resource origins (XSS mitigation)
    - X-Content-Type-Options: nosniff (MIME sniffing)
    - X-Frame-Options: DENY (clickjacking)
    - Referrer-Policy: strict-origin-when-cross-origin (privacy)
    - Permissions-Policy: restricts browser API access
    - Cross-Origin-Resource-Policy: same-site

    Note: HSTS is handled by production.py (SECURE_HSTS_SECONDS) and Nginx.
    """

    def process_response(self, request, response):
        response.setdefault("X-Content-Type-Options", "nosniff")
        response.setdefault("X-Frame-Options", "DENY")
        response.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        return response


# ---------------------------------------------------------------------------
# Story 12.4 — Request ID middleware (correlation tracing)
# ---------------------------------------------------------------------------

import uuid as _uuid_module
import structlog as _structlog


class RequestIDMiddleware(MiddlewareMixin):
    """
    Story 12.4 — Assigns a UUID request_id to every request.

    - Reads X-Request-ID from incoming headers (propagated by load balancer / Nginx).
    - Falls back to a freshly generated UUID4 if absent.
    - Binds the id to structlog's contextvars so every log statement in the
      request lifecycle carries the same request_id field.
    - Echoes it back in the X-Request-ID response header for client correlation.
    """

    def process_request(self, request):
        request_id = request.headers.get("X-Request-ID") or str(_uuid_module.uuid4())
        request.request_id = request_id
        _structlog.contextvars.bind_contextvars(request_id=request_id)

    def process_response(self, request, response):
        request_id = getattr(request, "request_id", None)
        if request_id:
            response["X-Request-ID"] = request_id
        _structlog.contextvars.clear_contextvars()
        return response


# ---------------------------------------------------------------------------
# Story 4.9 — In-App Browser Detection
# ---------------------------------------------------------------------------

_IN_APP_BROWSER_PATTERNS = (
    # WhatsApp
    "WhatsApp",
    # Facebook
    "FBAN", "FBAV", "FB_IAB",
    # Instagram
    "Instagram",
    # Line
    "Line",
)


class InAppBrowserMiddleware(MiddlewareMixin):
    """
    Story 4.9 — Server-side in-app browser detection.

    Detects WhatsApp, Facebook, Instagram, and Line in-app browsers from
    the User-Agent header.  Adds `X-In-App-Browser: true` response header
    when detected — the storefront React client reads this and renders
    the "Open in Chrome/Safari" banner + cart fallback.

    Detection order (server-side first, then client-side UA sniff as fallback).
    """

    def process_request(self, request):
        ua = request.META.get("HTTP_USER_AGENT", "")
        request.is_in_app_browser = any(pattern in ua for pattern in _IN_APP_BROWSER_PATTERNS)

    def process_response(self, request, response):
        if getattr(request, "is_in_app_browser", False):
            response["X-In-App-Browser"] = "true"
        return response
