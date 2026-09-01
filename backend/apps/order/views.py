"""
Order views — Stories 4.2, 4.3, 4.4, 4.8.

CartView:      GET/POST/DELETE /api/v1/store/cart/
CheckoutView:  POST /api/v1/store/checkout/
CartMergeView: POST /api/v1/store/cart/merge/
OrderDetailView: GET /api/v1/store/orders/{id}/
OrderStatusView: GET /api/v1/store/orders/{id}/status/
OrderConfirmView: POST /api/v1/store/orders/{id}/confirm/  (staff action)
"""

import uuid as uuid_mod

import structlog
from rest_framework.permissions import IsAuthenticated

from core.permissions import HasStore, IsStoreManager
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.order import cart as cart_service
from apps.order.models import CartSnapshot, InvalidOrderTransition, Order, OrderStatus
from apps.order.serializers import CheckoutInputSerializer, OrderSerializer

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Cart (Story 4.2)
# ---------------------------------------------------------------------------


class CartView(APIView):
    """
    Story 4.2 — Redis cart management.

    GET  /api/v1/store/cart/?cart_ref=<ref>   → retrieve cart items
    POST /api/v1/store/cart/                  → add item
    DELETE /api/v1/store/cart/                → remove item by variant_id

    cart_ref: anonymous session UUID (from cookie) or user UUID for auth users.
    30-day TTL refreshed on every write.
    """

    permission_classes = [HasStore]

    def _get_cart_ref(self, request) -> str:
        """Resolve cart_ref from request: user ID (auth) or session param (guest)."""
        if request.user and request.user.is_authenticated:
            return str(request.user.id)
        return request.query_params.get("cart_ref", "") or request.data.get("cart_ref", "")

    def get(self, request):
        cart_ref = self._get_cart_ref(request)
        if not cart_ref:
            return Response({"cart_ref": "", "items": [], "item_count": 0})

        items = cart_service.get_cart(str(request.store.id), cart_ref)
        return Response({"cart_ref": cart_ref, "items": items, "item_count": sum(i["quantity"] for i in items)})

    def post(self, request):
        """Add item to cart."""
        cart_ref = self._get_cart_ref(request)
        if not cart_ref:
            cart_ref = uuid_mod.uuid4().hex

        product_id = str(request.data.get("product_id", ""))
        variant_id = str(request.data.get("variant_id", ""))
        quantity = int(request.data.get("quantity", 1))

        if not product_id or not variant_id:
            return Response({"errors": [{"code": "PRODUCT_AND_VARIANT_REQUIRED"}]}, status=400)

        from apps.product.models import Variant

        try:
            variant = Variant.objects.get(id=variant_id, store=request.store)
        except Variant.DoesNotExist:
            return Response({"errors": [{"code": "VARIANT_NOT_FOUND"}]}, status=404)

        try:
            items = cart_service.add_to_cart(str(request.store.id), cart_ref, product_id, variant_id, quantity)
        except cart_service.CartServiceError:
            return Response({"errors": [{"code": "CART_SERVICE_UNAVAILABLE"}]}, status=503)

        return Response({"cart_ref": cart_ref, "items": items, "item_count": sum(i["quantity"] for i in items)})

    def delete(self, request):
        """Remove a line item by variant_id."""
        cart_ref = self._get_cart_ref(request)
        variant_id = str(request.data.get("variant_id", ""))
        if not variant_id:
            return Response({"errors": [{"code": "VARIANT_ID_REQUIRED"}]}, status=400)

        items = cart_service.remove_from_cart(str(request.store.id), cart_ref, variant_id)
        return Response({"cart_ref": cart_ref, "items": items, "item_count": sum(i["quantity"] for i in items)})


class CartMergeView(APIView):
    """
    Story 4.2 — Merge guest cart into authenticated user cart on login.
    POST /api/v1/store/cart/merge/
    Body: {"guest_ref": "<uuid>"}
    """

    permission_classes = [IsAuthenticated, HasStore]

    def post(self, request):
        guest_ref = request.data.get("guest_ref", "").strip()
        if not guest_ref:
            return Response({"errors": [{"code": "GUEST_REF_REQUIRED"}]}, status=400)

        user_ref = str(request.user.id)
        items = cart_service.merge_carts(str(request.store.id), guest_ref, user_ref)
        return Response({"cart_ref": user_ref, "items": items, "item_count": sum(i["quantity"] for i in items)})


# ---------------------------------------------------------------------------
# Checkout (Story 4.4)
# ---------------------------------------------------------------------------


class CheckoutView(APIView):
    """
    Story 4.4 — Guest checkout with M-Pesa payment.

    POST /api/v1/store/checkout/
    Body: {phone, name?, email?, delivery_address?, cart_ref}

    Flow:
    1. Validate cart items + check variant stock (409 if any out-of-stock)
    2. Write cart to PostgreSQL (safety-net before STK Push)
    3. Create Order in 'pending' status
    4. Initiate STK Push via initiate_payment()
    5. Return order_id + transaction_id

    On payment confirmation (webhook): payment_confirmed signal →
    order.transition_status('confirmed') → send_order_confirmation task.
    """

    permission_classes = [HasStore]

    def post(self, request):
        ser = CheckoutInputSerializer(data=request.data)
        if not ser.is_valid():
            return Response({"errors": ser.errors}, status=400)

        data = ser.validated_data
        cart_ref = data["cart_ref"]

        # Load cart
        items = cart_service.get_cart(str(request.store.id), cart_ref)
        if not items:
            return Response({"errors": [{"code": "CART_EMPTY"}]}, status=400)

        # Validate stock per variant
        from decimal import Decimal
        from apps.product.models import Variant

        variant_ids = [i["variant_id"] for i in items]
        variants = {
            str(v.id): v
            for v in Variant.objects.filter(id__in=variant_ids, store=request.store)
        }

        out_of_stock = []
        items_snapshot = []
        total_amount = Decimal("0.00")

        for item in items:
            vid = str(item["variant_id"])
            variant = variants.get(vid)
            if variant is None:
                return Response(
                    {"errors": [{"code": "VARIANT_NOT_FOUND", "variant_id": vid}]},
                    status=404,
                )
            if variant.inventory_count < item["quantity"]:
                out_of_stock.append(vid)
            else:
                line_total = variant.price * item["quantity"]
                total_amount += line_total
                items_snapshot.append({
                    "variant_id": vid,
                    "product_id": str(item["product_id"]),
                    "quantity": item["quantity"],
                    "price": str(variant.price),
                    "line_total": str(line_total),
                })

        if out_of_stock:
            return Response(
                {"errors": [{"code": "VARIANT_OUT_OF_STOCK", "variant_ids": out_of_stock}]},
                status=409,
            )

        from django.db import transaction as db_tx

        with db_tx.atomic():
            # Safety-net: write cart to PostgreSQL before STK Push
            snapshot = cart_service.write_cart_snapshot(request.store, cart_ref, items)

            # Create Order
            order = Order.objects.create(
                store=request.store,
                customer_phone=data["phone"],
                customer_name=data.get("name", ""),
                customer_email=data.get("email", ""),
                delivery_address=data.get("delivery_address"),
                items_snapshot=items_snapshot,
                total_amount=total_amount,
                customer=request.user if request.user.is_authenticated else None,
            )
            snapshot.linked_order = order
            snapshot.save(update_fields=["linked_order"])

        # Decrement inventory atomically
        from django.db.models import F
        for item in items:
            Variant.objects.filter(
                id=item["variant_id"], store=request.store
            ).update(inventory_count=F("inventory_count") - item["quantity"])

        # Initiate M-Pesa STK Push
        from apps.payment.exceptions import (
            InvalidPhoneNumberError,
            StkPushInitiationError,
            StkPushRateLimitedError,
        )
        from apps.payment.services import initiate_payment

        try:
            txn = initiate_payment(
                store=request.store,
                method="mpesa",
                amount=total_amount,
                phone=data["phone"],
                reference=f"order-{order.id}",
            )
            order.payment_transaction = txn
            order.save(update_fields=["payment_transaction"])
        except InvalidPhoneNumberError as exc:
            return Response({"errors": [{"code": "INVALID_PHONE", "message": str(exc)}]}, status=400)
        except StkPushRateLimitedError:
            return Response({"errors": [{"code": "RATE_LIMITED"}]}, status=429)
        except StkPushInitiationError as exc:
            return Response({"errors": [{"code": "PAYMENT_INITIATION_FAILED", "message": str(exc)}]}, status=502)

        log.info(
            "checkout_initiated",
            order_id=str(order.id),
            total=str(total_amount),
            store_id=str(request.store.id),
        )
        return Response({
            "order_id": str(order.id),
            "transaction_id": str(txn.id),
            "checkout_request_id": txn.checkout_request_id,
            "total_amount": str(total_amount),
            "message": "STK Push sent. Complete payment on your Safaricom phone.",
        }, status=201)


# ---------------------------------------------------------------------------
# Order management (Story 4.3)
# ---------------------------------------------------------------------------


class OrderDetailView(APIView):
    """
    Story 4.3 — Retrieve order detail.
    GET /api/v1/store/orders/{id}/
    """

    permission_classes = [HasStore]

    def get(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, store=request.store)
        except Order.DoesNotExist:
            return Response(status=404)
        return Response(OrderSerializer(order).data)


class OrderStatusView(APIView):
    """
    Story 4.3 / 4.8 — Lightweight order status polling.
    GET /api/v1/store/orders/{id}/status/
    Used by the storefront to check pending_payment_order_id from localStorage.
    Customer recovers their own order by UUID — store-scoped, no auth required.
    """

    permission_classes = [HasStore]

    def get(self, request, order_id):
        try:
            order = Order.objects.only("id", "status", "total_amount", "confirmed_at", "cancelled_at").get(
                id=order_id, store=request.store
            )
        except Order.DoesNotExist:
            return Response(status=404)

        return Response({
            "order_id": str(order.id),
            "status": order.status,
            "total_amount": str(order.total_amount),
            "confirmed_at": order.confirmed_at.isoformat() if order.confirmed_at else None,
            "cancelled_at": order.cancelled_at.isoformat() if order.cancelled_at else None,
        })


class OrderConfirmView(APIView):
    """
    Story 4.3 / 4.3b — Staff action: confirm a pending order.
    POST /api/v1/store/orders/{id}/confirm/
    """

    permission_classes = [IsStoreManager]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, store=request.store)
        except Order.DoesNotExist:
            return Response(status=404)

        try:
            order.transition_status(OrderStatus.CONFIRMED)
        except InvalidOrderTransition as exc:
            return Response(
                {"errors": [{"code": "INVALID_ORDER_TRANSITION", "message": str(exc)}]},
                status=422,
            )

        # Dispatch confirmation email via Celery (on_commit ensures DB commit first)
        from django.db import transaction as db_tx
        from apps.order.tasks import send_order_confirmation

        db_tx.on_commit(lambda: send_order_confirmation.apply_async(args=[str(order.id)]))

        log.info("order_confirmed", order_id=str(order.id))
        return Response(OrderSerializer(order).data)


class MerchantDashboardView(APIView):
    """
    Merchant dashboard data.
    GET /api/v1/store/dashboard/

    Returns data matching the admin frontend's IDashboardStats interface.
    """

    permission_classes = [IsStoreManager]

    def get(self, request):
        from decimal import Decimal

        from django.db.models import Sum, Count, Avg
        from django.utils import timezone

        from apps.analytics.models import HourlyOrderSummary
        from apps.order.models import Order

        now = timezone.localtime()
        today = now.date()
        current_hour = now.hour

        # Today's stats from HourlyOrderSummary
        hourly_rows = HourlyOrderSummary.objects.filter(
            store=request.store, date=today, hour__lte=current_hour
        ).aggregate(
            total_order_count=Sum("order_count"),
            total_revenue=Sum("revenue"),
        )
        today_count = hourly_rows["total_order_count"] or 0
        today_revenue = hourly_rows["total_revenue"] or Decimal("0")
        today_avg = (
            str(Decimal(str(today_revenue)) / today_count) if today_count > 0 else "0.00"
        )

        # Month stats
        month_start = today.replace(day=1)
        monthly = HourlyOrderSummary.objects.filter(
            store=request.store, date__gte=month_start, date__lte=today
        ).aggregate(
            total_order_count=Sum("order_count"),
            total_revenue=Sum("revenue"),
        )
        month_revenue = monthly["total_revenue"] or Decimal("0")
        month_count = monthly["total_order_count"] or 0

        # Product count
        from apps.product.models import Product, Variant, DEFAULT_LOW_STOCK_THRESHOLD
        from apps.store.models import StoreSettings

        total_products = Product.objects.filter(
            store=request.store, is_available=True
        ).count()

        # Low stock
        try:
            threshold = StoreSettings.objects.get(store=request.store).low_stock_threshold
        except StoreSettings.DoesNotExist:
            threshold = DEFAULT_LOW_STOCK_THRESHOLD

        low_stock_count = Variant.objects.filter(
            store=request.store,
            inventory_count__lte=threshold,
            is_available=True,
        ).count()

        # Active customers
        from apps.users.models import User
        active_customers = User.objects.filter(
            store=request.store,
            role=User.Role.CUSTOMER,
            is_active=True,
        ).count()

        # Recent orders
        recent_orders = Order.objects.filter(
            store=request.store,
        ).order_by("-created_at")[:10]

        from apps.order.serializers import OrderSerializer

        # Top products (by revenue today)
        from apps.order.models import CartSnapshot
        top_products = []
        today_orders = Order.objects.filter(
            store=request.store,
            created_at__date=today,
        )
        product_revenue = {}
        for order in today_orders:
            for item in order.items_snapshot:
                pid = item.get("product_id", "")
                pname = item.get("product_id", "Unknown")
                qty = item.get("quantity", 0)
                price = Decimal(str(item.get("price", "0")))
                if pid not in product_revenue:
                    product_revenue[pid] = {"product_name": pname, "quantity_sold": 0, "revenue": Decimal("0")}
                product_revenue[pid]["quantity_sold"] += qty
                product_revenue[pid]["revenue"] += price * qty

        # Sort by revenue and take top 5
        sorted_products = sorted(
            product_revenue.values(),
            key=lambda x: x["revenue"],
            reverse=True,
        )[:5]
        top_products = [
            {
                "product_name": p["product_name"],
                "quantity_sold": p["quantity_sold"],
                "revenue": str(p["revenue"]),
            }
            for p in sorted_products
        ]

        return Response({
            "data": {
                "today_revenue": str(today_revenue),
                "today_transactions": today_count,
                "today_avg_order": today_avg,
                "month_revenue": str(month_revenue),
                "month_transactions": month_count,
                "total_products": total_products,
                "low_stock_count": low_stock_count,
                "active_customers": active_customers,
                "recent_orders": OrderSerializer(recent_orders, many=True).data,
                "top_products": top_products,
            }
        })
