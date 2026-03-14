"""
Restaurant views.

Story 3.1: MenuSectionViewSet, MenuItemViewSet, ModifierGroupViewSet, ModifierViewSet
Story 3.2: PublicMenuView (no auth, SSR-friendly JSON for current service window)
Story 3.3: QRTokenGenerateView, QRTokenValidateView, TableViewSet
Story 3.4: TableSessionViewSet (open/assign-waiter/request-bill/close)

All management viewsets extend TenantViewSet for automatic tenant scoping.
"""

from django.db import IntegrityError
from django.db.models import Q, Prefetch
from django.utils import timezone

import structlog
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings

from core.pagination import StoreCursorPagination
from core.views import TenantViewSet

from apps.restaurant.models import (
    InvalidSessionTransition,
    MenuItem,
    MenuSection,
    Modifier,
    ModifierGroup,
    Table,
    TableSession,
)
from apps.restaurant.qr import QRTokenError, generate_qr_token, validate_qr_token
from apps.restaurant.serializers import (
    MenuItemSerializer,
    MenuSectionSerializer,
    ModifierGroupSerializer,
    ModifierSerializer,
    TableSessionSerializer,
)

log = structlog.get_logger(__name__)


def _filter_available_items(qs):
    """Return qs filtered to items within their time window (if any)."""
    now_time = timezone.localtime().time()
    return qs.filter(
        Q(available_from__isnull=True, available_until__isnull=True)
        | Q(
            available_from__isnull=False,
            available_until__isnull=False,
            available_from__lte=now_time,
            available_until__gte=now_time,
        )
        | Q(
            available_from__isnull=False,
            available_until__isnull=True,
            available_from__lte=now_time,
        )
        | Q(
            available_from__isnull=True,
            available_until__isnull=False,
            available_until__gte=now_time,
        )
    )


class MenuSectionViewSet(TenantViewSet):
    """CRUD for menu sections. Ordered by position then name."""

    serializer_class = MenuSectionSerializer
    queryset = MenuSection.objects.all()

    class _Pagination(StoreCursorPagination):
        ordering = "position"

    pagination_class = _Pagination


class MenuItemViewSet(TenantViewSet):
    """
    CRUD for menu items.

    List endpoint filters out items that are outside their scheduled availability
    window. Detail/create/update endpoints return/accept all items regardless of
    time window (admin needs to manage all items).
    """

    serializer_class = MenuItemSerializer
    queryset = MenuItem.objects.all()

    class _Pagination(StoreCursorPagination):
        ordering = "position"

    pagination_class = _Pagination

    def get_queryset(self):
        qs = super().get_queryset()

        # Time-based filtering on list action only
        if self.action == "list":
            qs = _filter_available_items(qs)

        return qs


class ModifierGroupViewSet(TenantViewSet):
    """CRUD for modifier groups."""

    serializer_class = ModifierGroupSerializer
    queryset = ModifierGroup.objects.all()

    class _Pagination(StoreCursorPagination):
        ordering = "name"

    pagination_class = _Pagination


class ModifierViewSet(TenantViewSet):
    """CRUD for modifiers."""

    serializer_class = ModifierSerializer
    queryset = Modifier.objects.all()

    class _Pagination(StoreCursorPagination):
        ordering = "name"

    pagination_class = _Pagination


class TableViewSet(TenantViewSet):
    """CRUD for restaurant tables — Story 3.3."""

    from apps.restaurant.serializers import TableSerializer as _Ser

    serializer_class = _Ser
    queryset = Table.objects.all()

    class _Pagination(StoreCursorPagination):
        ordering = "number"

    pagination_class = _Pagination


class TableSessionViewSet(TenantViewSet):
    """
    Story 3.4 — TableSession management.

    Standard CRUD is restricted to read-only; mutations go through explicit
    state-machine actions to prevent direct field assignment.

    POST   /api/v1/restaurant/sessions/                       → open new session
    GET    /api/v1/restaurant/sessions/{id}/                  → retrieve session
    PATCH  /api/v1/restaurant/sessions/{id}/assign-waiter/   → assign waiter
    PATCH  /api/v1/restaurant/sessions/{id}/request-bill/    → OPEN → BILL_REQUESTED
    PATCH  /api/v1/restaurant/sessions/{id}/close/           → BILL_REQUESTED → CLOSED
    """

    serializer_class = TableSessionSerializer
    queryset = TableSession.objects.select_related("table", "assigned_waiter")
    http_method_names = ["get", "post", "patch", "head", "options"]

    class _Pagination(StoreCursorPagination):
        ordering = "-opened_at"

    pagination_class = _Pagination

    def perform_create(self, serializer):
        """Open a new session — enforces one-OPEN-per-table via UniqueConstraint."""
        try:
            serializer.save(store=self.request.store, status=TableSession.STATUS_OPEN)
        except IntegrityError:
            from rest_framework.exceptions import ValidationError

            raise ValidationError(
                {"errors": [{"code": "DUPLICATE_SESSION", "message": "An OPEN session already exists for this table."}]},
            )

    def update(self, request, *args, **kwargs):
        # Prevent arbitrary PATCH to status — use dedicated transition actions.
        return Response(
            {"errors": [{"code": "METHOD_NOT_ALLOWED", "message": "Use /assign-waiter/, /request-bill/, or /close/ actions."}]},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=["patch"], url_path="assign-waiter")
    def assign_waiter(self, request, pk=None):
        """
        Assign the authenticated user (must be store_manager or store_owner) as
        the waiter for this session. Session must be OPEN.
        """
        session = self.get_object()
        if session.status != TableSession.STATUS_OPEN:
            return Response(
                {"errors": [{"code": "INVALID_SESSION_TRANSITION", "message": "Waiter can only be assigned to an OPEN session."}]},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        session.assigned_waiter = request.user
        session.save(update_fields=["assigned_waiter"])
        log.info("waiter_assigned", session_id=str(session.id), waiter_id=str(request.user.id))
        return Response(TableSessionSerializer(session, context={"request": request}).data)

    @action(detail=True, methods=["patch"], url_path="request-bill")
    def request_bill(self, request, pk=None):
        """Transition OPEN → BILL_REQUESTED."""
        session = self.get_object()
        try:
            session.transition(TableSession.STATUS_BILL_REQUESTED)
        except InvalidSessionTransition as exc:
            return Response(
                {"errors": [{"code": "INVALID_SESSION_TRANSITION", "message": str(exc)}]},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        log.info("session_bill_requested", session_id=str(session.id))
        return Response(TableSessionSerializer(session, context={"request": request}).data)

    @action(detail=True, methods=["patch"], url_path="close")
    def close(self, request, pk=None):
        """Transition BILL_REQUESTED → CLOSED."""
        session = self.get_object()
        try:
            session.transition(TableSession.STATUS_CLOSED)
        except InvalidSessionTransition as exc:
            return Response(
                {"errors": [{"code": "INVALID_SESSION_TRANSITION", "message": str(exc)}]},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        log.info("session_closed", session_id=str(session.id))
        return Response(TableSessionSerializer(session, context={"request": request}).data)


class QRTokenGenerateView(APIView):
    """
    Story 3.3 — Generate a signed QR token for a table.

    POST /api/v1/restaurant/tables/{id}/qr-token/
    """

    def post(self, request, table_id):
        try:
            table = Table.objects.get(id=table_id, store=request.store)
        except Table.DoesNotExist:
            return Response(status=404)

        secret = getattr(settings, "HMAC_QR_SECRET", "dev-qr-secret")
        token = generate_qr_token(
            store_id=str(table.store_id),
            table_id=str(table.id),
            secret=secret,
        )
        log.info("qr_token_generated", table_id=str(table.id))
        return Response({"token": token, "table_number": table.number})


class QRTokenValidateView(APIView):
    """
    Stories 3.3 + 3.5 — Validate a QR token.

    GET /api/v1/restaurant/qr/validate/?token=<token>

    Error messages are intentionally generic (Story 3.5 AC4): technical details
    about why a token failed are logged server-side but never exposed to the customer.
    """

    # User-facing messages — no technical details (Story 3.5 AC4)
    _USER_MESSAGES = {
        "INVALID_QR_TOKEN": "Invalid or damaged QR code. Please ask staff for help.",
        "QR_TOKEN_EXPIRED": "This QR code has expired. Please ask your waiter to refresh it.",
        "QR_TOKEN_ALREADY_USED": "This QR code has already been used. Please scan the current code on your table.",
    }

    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get("token", "")
        if not token:
            return Response(
                {"errors": [{"code": "INVALID_QR_TOKEN", "message": self._USER_MESSAGES["INVALID_QR_TOKEN"]}]},
                status=400,
            )

        from django_redis import get_redis_connection

        redis_client = get_redis_connection("default")
        secret = getattr(settings, "HMAC_QR_SECRET", "dev-qr-secret")

        try:
            payload = validate_qr_token(token, secret, redis_client)
        except QRTokenError as exc:
            # Log the real reason; return generic message to client
            log.warning("qr_token_validation_failed", code=exc.code, detail=str(exc))
            user_message = self._USER_MESSAGES.get(exc.code, self._USER_MESSAGES["INVALID_QR_TOKEN"])
            return Response(
                {"errors": [{"code": exc.code, "message": user_message}]},
                status=400,
            )

        # Load table and store details
        try:
            table = Table.objects.select_related("store").get(
                id=payload["table_id"],
                store_id=payload["store_id"],
            )
        except Table.DoesNotExist:
            log.warning("qr_token_table_not_found", table_id=payload.get("table_id"))
            return Response(
                {"errors": [{"code": "INVALID_QR_TOKEN", "message": self._USER_MESSAGES["INVALID_QR_TOKEN"]}]},
                status=400,
            )

        # Return current OPEN session if one exists (Story 3.4 integration)
        open_session = (
            TableSession.objects.filter(table=table, status=TableSession.STATUS_OPEN)
            .first()
        )

        return Response({
            "table_id": str(table.id),
            "table_number": table.number,
            "store_id": str(table.store_id),
            "store_name": table.store.name,
            # Confirmation text for AC1 — frontend renders this as-is
            "confirmation_prompt": f"You're joining Table {table.number}'s session at {table.store.name}. Is this correct?",
            # Fallback URL for AC2 — shown when customer taps "No, wrong table"
            "fallback_url": f"/t/{table.id}/",
            "open_session_id": str(open_session.id) if open_session else None,
        })


class PublicTableView(APIView):
    """
    Story 3.5 — Public table info endpoint. Used as fallback URL when a customer
    scans the wrong table's QR code.

    GET /t/{table_id}/
    Returns: table_number, store_name — enough for the customer to confirm which
    table they're at and ask staff for help.
    """

    permission_classes = [AllowAny]

    def get(self, request, table_id):
        try:
            table = Table.objects.select_related("store").get(id=table_id, is_active=True)
        except Table.DoesNotExist:
            return Response({"errors": [{"code": "TABLE_NOT_FOUND"}]}, status=404)

        return Response({
            "table_id": str(table.id),
            "table_number": table.number,
            "store_id": str(table.store_id),
            "store_name": table.store.name,
            "message": f"This is Table {table.number} at {table.store.name}. Please ask a staff member to scan the correct QR code for you.",
        })


class PublicMenuView(APIView):
    """
    Story 3.2 — Public menu endpoint.

    Returns all menu sections with their currently-available items for the
    resolved store. No authentication required (AllowAny).

    GET /api/v1/restaurant/public-menu/
    """

    permission_classes = [AllowAny]

    def get(self, request):
        store = getattr(request, "store", None)
        if store is None:
            return Response({"errors": [{"code": "STORE_NOT_FOUND"}]}, status=404)

        # Prefetch available items for performance (avoids N+1)
        available_items_qs = _filter_available_items(
            MenuItem.objects.filter(store=store, is_available=True)
        ).prefetch_related("modifier_groups__modifiers")

        sections = (
            MenuSection.objects.filter(store=store)
            .prefetch_related(
                Prefetch("items", queryset=available_items_qs)
            )
            .order_by("position", "name")
        )

        data = MenuSectionSerializer(sections, many=True).data
        log.info("public_menu_served", store_id=str(store.id))
        return Response({"data": data})
