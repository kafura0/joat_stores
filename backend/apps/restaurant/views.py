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

from core.permissions import HasStore, IsStoreManager

from django.conf import settings

from core.pagination import StoreCursorPagination
from core.views import TenantViewSet

from apps.restaurant.models import (
    BillShare,
    DineInOrder,
    InvalidSessionTransition,
    KitchenTicket,
    MenuItem,
    MenuSection,
    Modifier,
    ModifierGroup,
    PendingOrder,
    Reservation,
    Table,
    TableSession,
)
from apps.restaurant.qr import QRTokenError, generate_qr_token, validate_qr_token
from apps.restaurant.serializers import (
    BillShareSerializer,
    DineInOrderCreateSerializer,
    DineInOrderSerializer,
    KitchenTicketSerializer,
    MenuItemSerializer,
    MenuSectionSerializer,
    ModifierGroupSerializer,
    ModifierSerializer,
    PendingOrderCreateSerializer,
    PendingOrderLookupSerializer,
    PendingOrderSerializer,
    ReservationSerializer,
    SplitBillInputSerializer,
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

    def get_permissions(self):
        if self.action in ("list", "retrieve", "bill"):
            return super().get_permissions()
        return [IsStoreManager()]

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

    @action(detail=True, methods=["get"], url_path="bill")
    def bill(self, request, pk=None):
        """
        Story 3.11 — GET itemized bill for a session.

        GET /api/v1/restaurant/sessions/{id}/bill/
        Returns all orders + total; available once session is BILL_REQUESTED+.
        """
        session = self.get_object()

        orders = DineInOrder.objects.filter(
            session=session,
            status__in=[
                DineInOrder.STATUS_PENDING,
                DineInOrder.STATUS_CONFIRMED,
                DineInOrder.STATUS_READY,
            ],
        )

        total = sum(o.total_amount for o in orders)

        return Response({
            "session_id": str(session.id),
            "table_number": session.table.number,
            "session_status": session.status,
            "orders": DineInOrderSerializer(orders, many=True).data,
            "total_amount": str(total),
            "shares": BillShareSerializer(
                BillShare.objects.filter(session=session), many=True
            ).data,
        })

    @action(detail=True, methods=["post"], url_path="pay-bill")
    def pay_bill(self, request, pk=None):
        """
        Story 3.11 — Single-payer bill settlement via M-Pesa.

        POST /api/v1/restaurant/sessions/{id}/pay-bill/
        Body: {"phone": "+254712345678"}
        Creates one BillShare for full amount + initiates STK Push.
        """
        session = self.get_object()

        if session.status not in [TableSession.STATUS_BILL_REQUESTED, TableSession.STATUS_OPEN]:
            return Response(
                {"errors": [{"code": "INVALID_SESSION_STATUS", "message": "Request bill before paying."}]},
                status=400,
            )

        phone = request.data.get("phone", "").strip()
        if not phone:
            return Response({"errors": [{"code": "PHONE_REQUIRED"}]}, status=400)

        # Calculate total from all non-cancelled orders
        orders = DineInOrder.objects.filter(
            session=session,
            status__in=[DineInOrder.STATUS_PENDING, DineInOrder.STATUS_CONFIRMED, DineInOrder.STATUS_READY],
        )
        from decimal import Decimal as _Decimal
        total = sum(o.total_amount for o in orders) or _Decimal("0.00")

        share = BillShare.objects.create(
            store=session.store,
            session=session,
            payer_phone=phone,
            amount=total,
        )

        from apps.payment.exceptions import (
            InvalidPhoneNumberError,
            StkPushInitiationError,
            StkPushRateLimitedError,
        )
        from apps.payment.services import initiate_payment

        try:
            txn = initiate_payment(
                store=session.store,
                method="mpesa",
                amount=total,
                phone=phone,
                reference=f"bill-share-{share.id}",
            )
            share.payment_transaction = txn
            share.save(update_fields=["payment_transaction"])
        except InvalidPhoneNumberError as exc:
            return Response({"errors": [{"code": "INVALID_PHONE", "message": str(exc)}]}, status=400)
        except StkPushRateLimitedError as exc:
            return Response({"errors": [{"code": "RATE_LIMITED"}]}, status=429)
        except StkPushInitiationError as exc:
            return Response({"errors": [{"code": "PAYMENT_INITIATION_FAILED", "message": str(exc)}]}, status=502)

        log.info("bill_payment_initiated", session_id=str(session.id), share_id=str(share.id))
        return Response(BillShareSerializer(share).data, status=201)

    @action(detail=True, methods=["post"], url_path="split-bill")
    def split_bill(self, request, pk=None):
        """
        Story 3.11 — Split bill across multiple payers.

        POST /api/v1/restaurant/sessions/{id}/split-bill/
        Body: {"shares": [{"payer_phone": "+254...", "amount": "500.00", "items_snapshot": [...]}]}

        Creates one BillShare per person + initiates STK Push for each.
        """
        session = self.get_object()

        ser = SplitBillInputSerializer(data=request.data)
        if not ser.is_valid():
            return Response({"errors": ser.errors}, status=400)

        from apps.payment.exceptions import (
            InvalidPhoneNumberError,
            StkPushInitiationError,
            StkPushRateLimitedError,
        )
        from apps.payment.services import initiate_payment

        created_shares = []
        errors = []
        for share_data in ser.validated_data["shares"]:
            share = BillShare.objects.create(
                store=session.store,
                session=session,
                payer_phone=share_data["payer_phone"],
                amount=share_data["amount"],
                items_snapshot=share_data.get("items_snapshot", []),
            )
            try:
                txn = initiate_payment(
                    store=session.store,
                    method="mpesa",
                    amount=share_data["amount"],
                    phone=share_data["payer_phone"],
                    reference=f"bill-share-{share.id}",
                )
                share.payment_transaction = txn
                share.save(update_fields=["payment_transaction"])
                created_shares.append(share)
            except (InvalidPhoneNumberError, StkPushRateLimitedError, StkPushInitiationError) as exc:
                errors.append({"phone": share_data["payer_phone"], "error": str(exc)})

        log.info(
            "split_bill_initiated",
            session_id=str(session.id),
            total_shares=len(created_shares),
            errors=len(errors),
        )
        return Response({
            "shares": BillShareSerializer(created_shares, many=True).data,
            "errors": errors,
        }, status=201)


class QRTokenGenerateView(APIView):
    """
    Story 3.3 — Generate a signed QR token for a table.

    POST /api/v1/restaurant/tables/{id}/qr-token/
    """

    permission_classes = [IsStoreManager]

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


class TakeawayOrderView(APIView):
    """
    Story 3.10 — Place a takeaway order.

    POST /api/v1/restaurant/orders/takeaway/

    AllowAny — customer orders ahead from public menu.
    No session required (order_type='takeaway', session=None).
    Payment: POST /pending-orders/{id}/pay/ pattern with reference=f"takeaway-{id}".
    """

    permission_classes = [AllowAny]

    def post(self, request):
        store = getattr(request, "store", None)
        if store is None:
            return Response({"errors": [{"code": "STORE_NOT_FOUND"}]}, status=404)

        # Reuse DineInOrderCreateSerializer but session_id is not required for takeaway
        phone = request.data.get("phone", "").strip()
        if not phone:
            return Response({"errors": [{"code": "PHONE_REQUIRED"}]}, status=400)

        items_data = request.data.get("items", [])
        if not items_data:
            return Response({"errors": [{"code": "ITEMS_REQUIRED"}]}, status=400)

        item_ids = [item.get("menu_item_id") for item in items_data]
        modifier_ids = [
            mid
            for item in items_data
            for mid in item.get("selected_modifier_ids", [])
        ]

        menu_items = {
            str(mi.id): mi
            for mi in MenuItem.objects.filter(
                id__in=item_ids, store=store, is_available=True
            ).prefetch_related("modifier_groups__modifiers")
        }
        modifiers_by_id = {}
        for mi in menu_items.values():
            for grp in mi.modifier_groups.all():
                for mod in grp.modifiers.all():
                    modifiers_by_id[str(mod.id)] = mod

        missing_items = [str(iid) for iid in item_ids if str(iid) not in menu_items]
        if missing_items:
            return Response({"errors": [{"code": "ITEM_NOT_FOUND", "message": f"Items not found: {missing_items}"}]}, status=400)

        missing_mods = [str(mid) for mid in modifier_ids if str(mid) not in modifiers_by_id]
        if missing_mods:
            return Response({"errors": [{"code": "MODIFIER_NOT_FOUND", "message": f"Modifiers not found: {missing_mods}"}]}, status=400)

        from decimal import Decimal

        items_snapshot = []
        total_amount = Decimal("0.00")
        for item_input in items_data:
            mi = menu_items[str(item_input["menu_item_id"])]
            qty = int(item_input.get("quantity", 1))
            selected_modifiers = [modifiers_by_id[str(mid)] for mid in item_input.get("selected_modifier_ids", [])]
            mod_total = sum(m.price_addition for m in selected_modifiers)
            total_amount += (mi.price + mod_total) * qty
            items_snapshot.append({
                "menu_item_id": str(mi.id),
                "name": mi.name,
                "price": str(mi.price),
                "quantity": qty,
                "contains_allergens": mi.contains_allergens,
                "modifiers": [{"modifier_id": str(m.id), "name": m.name, "price_addition": str(m.price_addition)} for m in selected_modifiers],
            })

        from django.db import transaction as db_transaction

        with db_transaction.atomic():
            order = DineInOrder.objects.create(
                store=store,
                session=None,  # No table session for takeaway
                items_snapshot=items_snapshot,
                total_amount=total_amount,
                order_type=DineInOrder.ORDER_TYPE_TAKEAWAY,
            )
            KitchenTicket.objects.create(
                store=store,
                order=order,
                items_snapshot=items_snapshot,
                waiter_name="",
                table_number=0,  # No table for takeaway
            )

        log.info("takeaway_order_created", order_id=str(order.id), store_id=str(store.id))
        return Response({
            **DineInOrderSerializer(order).data,
            "payment_url": f"/api/v1/restaurant/pending-orders/{order.id}/pay/",
            "phone": phone,
        }, status=201)


class TakeawayOrderPayView(APIView):
    """
    Story 3.10 — Initiate M-Pesa payment for a takeaway order.

    POST /api/v1/restaurant/orders/takeaway/{order_id}/pay/
    AllowAny — customer pays before pickup.
    """

    permission_classes = [AllowAny]

    def post(self, request, order_id):
        store = getattr(request, "store", None)
        if store is None:
            return Response({"errors": [{"code": "STORE_NOT_FOUND"}]}, status=404)

        try:
            order = DineInOrder.objects.get(
                id=order_id,
                store=store,
                order_type=DineInOrder.ORDER_TYPE_TAKEAWAY,
            )
        except DineInOrder.DoesNotExist:
            return Response({"errors": [{"code": "ORDER_NOT_FOUND"}]}, status=404)

        phone = request.data.get("phone", "").strip()
        if not phone:
            return Response({"errors": [{"code": "PHONE_REQUIRED"}]}, status=400)

        from apps.payment.exceptions import (
            InvalidPhoneNumberError,
            StkPushInitiationError,
            StkPushRateLimitedError,
        )
        from apps.payment.services import initiate_payment

        try:
            txn = initiate_payment(
                store=store,
                method="mpesa",
                amount=order.total_amount,
                phone=phone,
                reference=f"takeaway-{order.id}",
            )
        except InvalidPhoneNumberError as exc:
            return Response({"errors": [{"code": "INVALID_PHONE", "message": str(exc)}]}, status=400)
        except StkPushRateLimitedError as exc:
            return Response(
                {"errors": [{"code": "RATE_LIMITED", "message": f"Retry after {exc.retry_after.isoformat()}."}]},
                status=429,
            )
        except StkPushInitiationError as exc:
            return Response({"errors": [{"code": "PAYMENT_INITIATION_FAILED", "message": str(exc)}]}, status=502)

        log.info("takeaway_payment_initiated", order_id=str(order.id), txn_id=str(txn.id))
        return Response({
            "message": "STK Push sent. Complete payment on your phone.",
            "transaction_id": str(txn.id),
            "checkout_request_id": txn.checkout_request_id,
        })


class DineInOrderView(APIView):
    """
    Story 3.6 — Place a dine-in order.

    POST /api/v1/restaurant/orders/

    Validates items, builds denormalized items_snapshot in a single prefetch
    query, calculates total_amount, creates DineInOrder + KitchenTicket atomically.
    """

    permission_classes = [HasStore]

    def post(self, request):
        store = request.store
        ser = DineInOrderCreateSerializer(data=request.data)
        if not ser.is_valid():
            return Response({"errors": ser.errors}, status=400)

        data = ser.validated_data

        # Load session — must be OPEN and belong to this store
        try:
            session = (
                TableSession.objects.select_related("table", "assigned_waiter")
                .get(id=data["session_id"], store=store, status=TableSession.STATUS_OPEN)
            )
        except TableSession.DoesNotExist:
            return Response(
                {"errors": [{"code": "SESSION_NOT_FOUND", "message": "No OPEN session found for this store with that ID."}]},
                status=404,
            )

        # Collect all requested item + modifier IDs
        item_ids = [item["menu_item_id"] for item in data["items"]]
        modifier_ids = [
            mid
            for item in data["items"]
            for mid in item.get("selected_modifier_ids", [])
        ]

        # Single prefetch query — satisfies AC1 (no more than one join at query time)
        menu_items = {
            str(mi.id): mi
            for mi in MenuItem.objects.filter(
                id__in=item_ids, store=store, is_available=True
            ).prefetch_related("modifier_groups__modifiers")
        }

        modifiers_by_id = {}
        for mi in menu_items.values():
            for grp in mi.modifier_groups.all():
                for mod in grp.modifiers.all():
                    modifiers_by_id[str(mod.id)] = mod

        # Validate all requested IDs exist
        missing_items = [str(iid) for iid in item_ids if str(iid) not in menu_items]
        if missing_items:
            return Response(
                {"errors": [{"code": "ITEM_NOT_FOUND", "message": f"Items not found or unavailable: {missing_items}"}]},
                status=400,
            )

        missing_mods = [str(mid) for mid in modifier_ids if str(mid) not in modifiers_by_id]
        if missing_mods:
            return Response(
                {"errors": [{"code": "MODIFIER_NOT_FOUND", "message": f"Modifiers not found: {missing_mods}"}]},
                status=400,
            )

        # Build denormalized snapshot
        from decimal import Decimal

        items_snapshot = []
        total_amount = Decimal("0.00")

        for item_input in data["items"]:
            mi = menu_items[str(item_input["menu_item_id"])]
            qty = item_input["quantity"]
            selected_modifiers = [
                modifiers_by_id[str(mid)]
                for mid in item_input.get("selected_modifier_ids", [])
            ]
            mod_total = sum(m.price_addition for m in selected_modifiers)
            line_total = (mi.price + mod_total) * qty
            total_amount += line_total

            items_snapshot.append({
                "menu_item_id": str(mi.id),
                "name": mi.name,
                "price": str(mi.price),
                "quantity": qty,
                "contains_allergens": mi.contains_allergens,
                "modifiers": [
                    {
                        "modifier_id": str(m.id),
                        "name": m.name,
                        "price_addition": str(m.price_addition),
                    }
                    for m in selected_modifiers
                ],
            })

        # Denormalize waiter name
        waiter_name = ""
        if session.assigned_waiter_id:
            w = session.assigned_waiter
            waiter_name = w.get_full_name() or w.email

        # Atomic create: DineInOrder + KitchenTicket
        from django.db import transaction

        with transaction.atomic():
            order = DineInOrder.objects.create(
                store=store,
                session=session,
                items_snapshot=items_snapshot,
                total_amount=total_amount,
            )
            KitchenTicket.objects.create(
                store=store,
                order=order,
                items_snapshot=items_snapshot,
                waiter_name=waiter_name,
                table_number=session.table.number,
            )

        log.info(
            "dineinorder_created",
            order_id=str(order.id),
            session_id=str(session.id),
            total=str(total_amount),
        )
        return Response(DineInOrderSerializer(order).data, status=201)


class KitchenTicketListView(APIView):
    """
    Story 3.6 — Kitchen display endpoint.

    GET /api/v1/restaurant/kitchen/tickets/

    Returns only PENDING and IN_PROGRESS tickets for the resolved store.
    All ticket data is fully denormalized — zero joins needed.
    Target response time: < 50ms.
    """

    permission_classes = [HasStore]

    def get(self, request):
        store = request.store
        tickets = KitchenTicket.objects.filter(
            store=store,
            status__in=[KitchenTicket.STATUS_PENDING, KitchenTicket.STATUS_IN_PROGRESS],
        ).only("id", "order_id", "status", "items_snapshot", "waiter_name", "table_number", "created_at")

        return Response({"data": KitchenTicketSerializer(tickets, many=True).data})


class KitchenTicketUpdateView(APIView):
    """
    Story 3.6 — Update kitchen ticket status.

    PATCH /api/v1/restaurant/kitchen/tickets/{ticket_id}/
    Body: {"status": "IN_PROGRESS" | "COMPLETED" | "CANCELLED"}
    """

    permission_classes = [IsStoreManager]

    def patch(self, request, ticket_id):
        store = request.store
        try:
            ticket = KitchenTicket.objects.get(id=ticket_id, store=store)
        except KitchenTicket.DoesNotExist:
            return Response(status=404)

        new_status = request.data.get("status")
        if not new_status:
            return Response({"errors": [{"code": "STATUS_REQUIRED"}]}, status=400)

        try:
            ticket.transition(new_status)
        except InvalidSessionTransition as exc:
            return Response(
                {"errors": [{"code": "INVALID_TICKET_TRANSITION", "message": str(exc)}]},
                status=422,
            )

        # Mirror status on the DineInOrder for Story 3.6b
        status_map = {
            KitchenTicket.STATUS_IN_PROGRESS: DineInOrder.STATUS_CONFIRMED,
            KitchenTicket.STATUS_COMPLETED: DineInOrder.STATUS_READY,
            KitchenTicket.STATUS_CANCELLED: DineInOrder.STATUS_CANCELLED,
        }
        if new_status in status_map:
            DineInOrder.objects.filter(id=ticket.order_id).update(status=status_map[new_status])

        # Story 3.10: notify takeaway customer when order is READY
        if new_status == KitchenTicket.STATUS_COMPLETED:
            order = DineInOrder.objects.filter(id=ticket.order_id, order_type=DineInOrder.ORDER_TYPE_TAKEAWAY).first()
            if order:
                from apps.restaurant.tasks import notify_takeaway_ready
                notify_takeaway_ready.apply_async(args=[str(order.id)], countdown=0)

        log.info("kitchen_ticket_updated", ticket_id=str(ticket.id), status=new_status)
        return Response(KitchenTicketSerializer(ticket).data)


class OrderStatusView(APIView):
    """
    Story 3.6b — Customer order status polling endpoint.

    GET /api/v1/restaurant/orders/{order_id}/status/

    Returns DineInOrder status + KitchenTicket status. Used by TanStack Query
    on the customer confirmation screen (refetchInterval: 10000ms).
    """

    permission_classes = [AllowAny]

    def get(self, request, order_id):
        try:
            order = DineInOrder.objects.select_related("session__table", "ticket").get(id=order_id)
        except DineInOrder.DoesNotExist:
            return Response(status=404)

        ticket_status = None
        try:
            ticket_status = order.ticket.status
        except KitchenTicket.DoesNotExist:
            pass

        return Response({
            "order_id": str(order.id),
            "order_status": order.status,
            "ticket_status": ticket_status,
            "table_number": order.session.table.number,
            "total_amount": str(order.total_amount),
            "items_snapshot": order.items_snapshot,
            "placed_at": order.placed_at.isoformat(),
        })


class PendingOrderCreateView(APIView):
    """
    Story 3.7 — Create a PendingOrder (customer pre-arrival order).

    POST /api/v1/restaurant/pending-orders/
    AllowAny — customer browses public menu and submits before arriving.
    Returns: order summary + 6-digit PIN.
    """

    permission_classes = [HasStore]

    def post(self, request):
        store = request.store
        ser = PendingOrderCreateSerializer(data=request.data)
        if not ser.is_valid():
            return Response({"errors": ser.errors}, status=400)

        data = ser.validated_data

        # Validate and build snapshot (same logic as DineInOrderView)
        item_ids = [item["menu_item_id"] for item in data["items"]]
        modifier_ids = [
            mid
            for item in data["items"]
            for mid in item.get("selected_modifier_ids", [])
        ]

        menu_items = {
            str(mi.id): mi
            for mi in MenuItem.objects.filter(
                id__in=item_ids, store=store, is_available=True
            ).prefetch_related("modifier_groups__modifiers")
        }
        modifiers_by_id = {}
        for mi in menu_items.values():
            for grp in mi.modifier_groups.all():
                for mod in grp.modifiers.all():
                    modifiers_by_id[str(mod.id)] = mod

        missing_items = [str(iid) for iid in item_ids if str(iid) not in menu_items]
        if missing_items:
            return Response(
                {"errors": [{"code": "ITEM_NOT_FOUND", "message": f"Items not found or unavailable: {missing_items}"}]},
                status=400,
            )

        missing_mods = [str(mid) for mid in modifier_ids if str(mid) not in modifiers_by_id]
        if missing_mods:
            return Response(
                {"errors": [{"code": "MODIFIER_NOT_FOUND", "message": f"Modifiers not found: {missing_mods}"}]},
                status=400,
            )

        from decimal import Decimal
        from django.utils import timezone
        import datetime

        items_snapshot = []
        total_amount = Decimal("0.00")
        for item_input in data["items"]:
            mi = menu_items[str(item_input["menu_item_id"])]
            qty = item_input["quantity"]
            selected_modifiers = [modifiers_by_id[str(mid)] for mid in item_input.get("selected_modifier_ids", [])]
            mod_total = sum(m.price_addition for m in selected_modifiers)
            total_amount += (mi.price + mod_total) * qty
            items_snapshot.append({
                "menu_item_id": str(mi.id),
                "name": mi.name,
                "price": str(mi.price),
                "quantity": qty,
                "contains_allergens": mi.contains_allergens,
                "modifiers": [{"modifier_id": str(m.id), "name": m.name, "price_addition": str(m.price_addition)} for m in selected_modifiers],
            })

        order = PendingOrder.objects.create(
            store=store,
            phone=data["phone"],
            items_snapshot=items_snapshot,
            total_amount=total_amount,
            expires_at=timezone.now() + datetime.timedelta(hours=24),
        )

        log.info("pending_order_created", order_id=str(order.id), phone=order.phone)
        return Response(PendingOrderSerializer(order).data, status=201)


class PendingOrderLookupView(APIView):
    """
    Story 3.7 — Waiter lookup: find a PendingOrder by PIN or phone.

    GET /api/v1/restaurant/pending-orders/lookup/?pin=123456
    GET /api/v1/restaurant/pending-orders/lookup/?phone=+254712345678
    """

    permission_classes = [HasStore]

    def get(self, request):
        store = request.store
        pin = request.query_params.get("pin", "").strip()
        phone = request.query_params.get("phone", "").strip()

        if not pin and not phone:
            return Response({"errors": [{"code": "LOOKUP_PARAM_REQUIRED", "message": "Provide pin or phone."}]}, status=400)

        qs = PendingOrder.objects.filter(
            store=store,
            status__in=[PendingOrder.STATUS_PENDING, PendingOrder.STATUS_PAID],
        )
        if pin:
            qs = qs.filter(pin=pin)
        else:
            qs = qs.filter(phone=phone)

        order = qs.first()
        if order is None:
            return Response({"errors": [{"code": "PENDING_ORDER_NOT_FOUND"}]}, status=404)

        return Response(PendingOrderLookupSerializer(order).data)


class PendingOrderPayView(APIView):
    """
    Story 3.8 — Initiate advance M-Pesa payment for a PendingOrder.

    POST /api/v1/restaurant/pending-orders/{id}/pay/
    AllowAny — customer pays before arriving.

    On success: STK Push sent; status remains PENDING until webhook confirms.
    On webhook confirmation: payment_confirmed signal → status→PAID.
    """

    permission_classes = [HasStore]

    def post(self, request, order_id):
        store = request.store
        try:
            pending = PendingOrder.objects.get(
                id=order_id,
                store=store,
                status=PendingOrder.STATUS_PENDING,
            )
        except PendingOrder.DoesNotExist:
            return Response({"errors": [{"code": "PENDING_ORDER_NOT_FOUND"}]}, status=404)

        from apps.payment.exceptions import (
            InvalidPhoneNumberError,
            StkPushInitiationError,
            StkPushRateLimitedError,
        )
        from apps.payment.services import initiate_payment

        try:
            txn = initiate_payment(
                store=store,
                method="mpesa",
                amount=pending.total_amount,
                phone=pending.phone,
                reference=f"pending-{pending.id}",
            )
        except InvalidPhoneNumberError as exc:
            return Response({"errors": [{"code": "INVALID_PHONE", "message": str(exc)}]}, status=400)
        except StkPushRateLimitedError as exc:
            return Response(
                {"errors": [{"code": "RATE_LIMITED", "message": f"Too many payment attempts. Retry after {exc.retry_after.isoformat()}."}]},
                status=429,
            )
        except StkPushInitiationError as exc:
            return Response({"errors": [{"code": "PAYMENT_INITIATION_FAILED", "message": str(exc)}]}, status=502)

        log.info("pending_order_payment_initiated", order_id=str(pending.id), txn_id=str(txn.id))
        return Response({
            "message": "STK Push sent. Complete payment on your phone.",
            "transaction_id": str(txn.id),
            "checkout_request_id": txn.checkout_request_id,
        })


class PendingOrderConvertView(APIView):
    """
    Story 3.7/3.8 — Waiter: convert PendingOrder to DineInOrder + KitchenTicket.

    POST /api/v1/restaurant/pending-orders/{id}/convert/
    Body: {"session_id": "<uuid>"}

    If the PendingOrder is PAID, the MpesaTransaction is linked to the resulting DineInOrder.
    """

    permission_classes = [IsStoreManager]

    def post(self, request, order_id):
        store = request.store
        try:
            pending = PendingOrder.objects.get(
                id=order_id,
                store=store,
                status__in=[PendingOrder.STATUS_PENDING, PendingOrder.STATUS_PAID],
            )
        except PendingOrder.DoesNotExist:
            return Response({"errors": [{"code": "PENDING_ORDER_NOT_FOUND"}]}, status=404)

        session_id = request.data.get("session_id")
        if not session_id:
            return Response({"errors": [{"code": "SESSION_ID_REQUIRED"}]}, status=400)

        try:
            session = TableSession.objects.select_related("table", "assigned_waiter").get(
                id=session_id, store=store, status=TableSession.STATUS_OPEN
            )
        except TableSession.DoesNotExist:
            return Response({"errors": [{"code": "SESSION_NOT_FOUND"}]}, status=404)

        waiter_name = ""
        if session.assigned_waiter_id:
            w = session.assigned_waiter
            waiter_name = w.get_full_name() or w.email

        # Look up the confirmed payment transaction if this was a PAID order (Story 3.8)
        payment_txn = None
        if pending.status == PendingOrder.STATUS_PAID:
            from apps.payment.models import MpesaTransaction, MpesaTransactionStatus

            payment_txn = (
                MpesaTransaction.objects.filter(
                    store=store,
                    reference=f"pending-{pending.id}",
                    status=MpesaTransactionStatus.CONFIRMED,
                )
                .first()
            )

        from django.db import transaction as db_transaction

        with db_transaction.atomic():
            order = DineInOrder.objects.create(
                store=store,
                session=session,
                items_snapshot=pending.items_snapshot,
                total_amount=pending.total_amount,
                status=DineInOrder.STATUS_PENDING,
                payment_transaction=payment_txn,
            )
            KitchenTicket.objects.create(
                store=store,
                order=order,
                items_snapshot=pending.items_snapshot,
                waiter_name=waiter_name,
                table_number=session.table.number,
            )
            pending.status = PendingOrder.STATUS_CONVERTED
            pending.converted_order = order
            pending.save(update_fields=["status", "converted_order"])

        log.info(
            "pending_order_converted",
            pending_id=str(pending.id),
            order_id=str(order.id),
            session_id=str(session.id),
            paid=payment_txn is not None,
        )
        return Response(DineInOrderSerializer(order).data, status=201)


class ReservationViewSet(TenantViewSet):
    """
    Story 3.9 — Reservation management.

    POST   /api/v1/restaurant/reservations/          → create (dispatches notification)
    GET    /api/v1/restaurant/reservations/{id}/     → retrieve
    PATCH  /api/v1/restaurant/reservations/{id}/confirm/   → PENDING→CONFIRMED
    PATCH  /api/v1/restaurant/reservations/{id}/seat/      → CONFIRMED→SEATED + TableSession
    PATCH  /api/v1/restaurant/reservations/{id}/no-show/   → CONFIRMED→NO_SHOW
    """

    serializer_class = ReservationSerializer
    queryset = Reservation.objects.select_related("table", "session")
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return super().get_permissions()
        return [IsStoreManager()]

    class _Pagination(StoreCursorPagination):
        ordering = "reserved_for"

    pagination_class = _Pagination

    def perform_create(self, serializer):
        reservation = serializer.save(store=self.request.store)
        # Dispatch notification within 60s (Story 3.9 AC1)
        from apps.restaurant.tasks import send_reservation_notification

        send_reservation_notification.apply_async(
            args=[str(reservation.id), "created"],
            countdown=0,
        )
        log.info("reservation_created", reservation_id=str(reservation.id))

    def update(self, request, *args, **kwargs):
        return Response(
            {"errors": [{"code": "METHOD_NOT_ALLOWED", "message": "Use /confirm/, /seat/, or /no-show/ actions."}]},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=["patch"], url_path="confirm")
    def confirm(self, request, pk=None):
        """PENDING → CONFIRMED."""
        reservation = self.get_object()
        try:
            reservation.transition(Reservation.STATUS_CONFIRMED)
        except InvalidSessionTransition as exc:
            return Response(
                {"errors": [{"code": "INVALID_RESERVATION_TRANSITION", "message": str(exc)}]},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        from apps.restaurant.tasks import send_reservation_notification
        send_reservation_notification.apply_async(args=[str(reservation.id), "confirmed"], countdown=0)
        log.info("reservation_confirmed", reservation_id=str(reservation.id))
        return Response(ReservationSerializer(reservation, context={"request": request}).data)

    @action(detail=True, methods=["patch"], url_path="seat")
    def seat(self, request, pk=None):
        """CONFIRMED → SEATED + auto-create TableSession for the reserved table."""
        reservation = self.get_object()

        if reservation.table is None:
            return Response(
                {"errors": [{"code": "TABLE_NOT_ASSIGNED", "message": "Assign a table to the reservation before seating."}]},
                status=400,
            )

        try:
            reservation.transition(Reservation.STATUS_SEATED)
        except InvalidSessionTransition as exc:
            return Response(
                {"errors": [{"code": "INVALID_RESERVATION_TRANSITION", "message": str(exc)}]},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        # Auto-create OPEN TableSession (DB enforces uniqueness)
        try:
            session = TableSession.objects.create(
                store=reservation.store,
                table=reservation.table,
                status=TableSession.STATUS_OPEN,
            )
            reservation.session = session
            reservation.save(update_fields=["session"])
        except Exception:
            from django.db import IntegrityError as _IntegrityError
            return Response(
                {"errors": [{"code": "DUPLICATE_SESSION", "message": "An OPEN session already exists for this table."}]},
                status=409,
            )

        from apps.restaurant.tasks import send_reservation_notification
        send_reservation_notification.apply_async(args=[str(reservation.id), "seated"], countdown=0)
        log.info("reservation_seated", reservation_id=str(reservation.id), session_id=str(session.id))
        return Response(ReservationSerializer(reservation, context={"request": request}).data)

    @action(detail=True, methods=["patch"], url_path="no-show")
    def no_show(self, request, pk=None):
        """CONFIRMED → NO_SHOW."""
        reservation = self.get_object()
        try:
            reservation.transition(Reservation.STATUS_NO_SHOW)
        except InvalidSessionTransition as exc:
            return Response(
                {"errors": [{"code": "INVALID_RESERVATION_TRANSITION", "message": str(exc)}]},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        from apps.restaurant.tasks import send_reservation_notification
        send_reservation_notification.apply_async(args=[str(reservation.id), "no_show"], countdown=0)
        log.info("reservation_no_show", reservation_id=str(reservation.id))
        return Response(ReservationSerializer(reservation, context={"request": request}).data)


class PublicMenuView(APIView):
    """
    Story 3.2 — Public menu endpoint.

    Returns all menu sections with their currently-available items for the
    resolved store. No authentication required (AllowAny).

    GET /api/v1/restaurant/public-menu/
    """

    permission_classes = [HasStore]

    def get(self, request):
        store = request.store

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
