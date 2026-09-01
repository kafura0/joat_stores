"""
Additional merchant API views — order list, customers, inventory, staff.

These complement the existing views in order/views.py, product/views.py, etc.
All endpoints are store-scoped via TenantViewSet or HasStore permission.
"""

from decimal import Decimal

from django.db.models import Sum, Count, Q
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pagination import StoreCursorPagination
from core.permissions import HasStore, IsStoreManager


# ---------------------------------------------------------------------------
# Order List
# ---------------------------------------------------------------------------


class OrderListView(APIView):
    """
    GET /api/v1/store/orders/
    Returns all orders for the store, newest first.
    """

    permission_classes = [HasStore]
    pagination_class = StoreCursorPagination

    def get(self, request):
        from apps.order.models import Order

        qs = Order.objects.filter(store=request.store).order_by("-created_at")

        # Optional filters
        status = request.query_params.get("status")
        if status:
            qs = qs.filter(status=status)

        payment_method = request.query_params.get("payment_method")
        if payment_method:
            qs = qs.filter(payment_transaction__method=payment_method)

        # Paginate
        page = self.paginate_queryset(qs, request)
        if page is not None:
            from apps.order.serializers import OrderSerializer

            serializer = OrderSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        from apps.order.serializers import OrderSerializer

        return Response({"data": OrderSerializer(qs[:50], many=True).data})

    @property
    def paginator(self):
        if not hasattr(self, "_paginator"):
            self._paginator = self.pagination_class()
        return self._paginator

    def paginate_queryset(self, queryset, request):
        return self.paginator.paginate_queryset(queryset, request, view=self)

    def get_paginated_response(self, data):
        return self.paginator.get_paginated_response(data)


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------


class CustomerListView(APIView):
    """
    GET  /api/v1/store/customers/ — list customers (users with role=customer)
    POST /api/v1/store/customers/ — create a customer
    """

    permission_classes = [HasStore]

    def get(self, request):
        from apps.users.models import User

        search = request.query_params.get("search", "")
        qs = User.objects.filter(
            store=request.store,
            role=User.Role.CUSTOMER,
            is_active=True,
        )

        if search:
            qs = qs.filter(
                Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )

        customers = []
        for user in qs[:100]:
            # Count orders and total spent
            from apps.order.models import Order

            order_stats = Order.objects.filter(
                store=request.store,
                customer=user,
            ).aggregate(
                total_orders=Count("id"),
                total_spent=Sum("total_amount"),
            )

            customers.append({
                "id": user.id,
                "name": user.get_full_name() or user.email,
                "email": user.email,
                "phone": getattr(user, "phone", ""),
                "total_orders": order_stats["total_orders"] or 0,
                "total_spent": str(order_stats["total_spent"] or "0.00"),
                "created_at": user.date_joined.isoformat(),
            })

        return Response({
            "data": customers,
            "meta": {"count": len(customers)},
        })

    def post(self, request):
        from apps.users.models import User

        email = request.data.get("email", "").strip()
        first_name = request.data.get("first_name", "").strip()
        last_name = request.data.get("last_name", "").strip()
        phone = request.data.get("phone", "").strip()

        if not email:
            return Response(
                {"errors": [{"field": "email", "message": "Email is required", "code": "REQUIRED"}]},
                status=400,
            )

        if User.objects.filter(email=email, store=request.store).exists():
            return Response(
                {"errors": [{"field": "email", "message": "Customer already exists", "code": "DUPLICATE"}]},
                status=400,
            )

        user = User.objects.create(
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=User.Role.CUSTOMER,
            store=request.store,
            is_active=True,
        )

        return Response({
            "data": {
                "id": user.id,
                "name": user.get_full_name() or user.email,
                "email": user.email,
                "phone": phone,
                "total_orders": 0,
                "total_spent": "0.00",
                "created_at": user.date_joined.isoformat(),
            }
        }, status=201)


class CustomerDetailView(APIView):
    """
    GET /api/v1/store/customers/{id}/
    """

    permission_classes = [HasStore]

    def get(self, request, customer_id):
        from apps.users.models import User
        from apps.order.models import Order

        try:
            user = User.objects.get(
                id=customer_id,
                store=request.store,
                role=User.Role.CUSTOMER,
            )
        except User.DoesNotExist:
            return Response(status=404)

        order_stats = Order.objects.filter(
            store=request.store,
            customer=user,
        ).aggregate(
            total_orders=Count("id"),
            total_spent=Sum("total_amount"),
        )

        return Response({
            "data": {
                "id": user.id,
                "name": user.get_full_name() or user.email,
                "email": user.email,
                "phone": getattr(user, "phone", ""),
                "total_orders": order_stats["total_orders"] or 0,
                "total_spent": str(order_stats["total_spent"] or "0.00"),
                "created_at": user.date_joined.isoformat(),
            }
        })


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------


class InventoryListView(APIView):
    """
    GET /api/v1/store/inventory/
    Returns stock levels for all variants in the store.
    """

    permission_classes = [HasStore]

    def get(self, request):
        from apps.product.models import Variant
        from apps.store.models import StoreSettings
        from apps.product.models import DEFAULT_LOW_STOCK_THRESHOLD

        try:
            threshold = StoreSettings.objects.get(store=request.store).low_stock_threshold
        except StoreSettings.DoesNotExist:
            threshold = DEFAULT_LOW_STOCK_THRESHOLD

        search = request.query_params.get("search", "")
        status_filter = request.query_params.get("status", "")

        qs = Variant.objects.filter(
            store=request.store,
            is_available=True,
        ).select_related("product")

        if search:
            qs = qs.filter(
                Q(product__name__icontains=search)
                | Q(sku__icontains=search)
            )

        items = []
        for v in qs[:200]:
            if v.inventory_count <= 0:
                status = "out_of_stock"
            elif v.inventory_count <= threshold:
                status = "low_stock"
            else:
                status = "in_stock"

            if status_filter and status != status_filter:
                continue

            items.append({
                "variant_id": v.id,
                "product_name": v.product.name,
                "variant_name": " / ".join(v.attribute_values.values()) if v.attribute_values else "Default",
                "sku": v.sku,
                "current_stock": v.inventory_count,
                "low_stock_threshold": threshold,
                "status": status,
            })

        return Response({"data": items})


# ---------------------------------------------------------------------------
# Staff (users with store_owner, store_manager, cashier, waiter roles)
# ---------------------------------------------------------------------------


class StaffListView(APIView):
    """
    GET  /api/v1/store/users/ — list staff for this store
    POST /api/v1/store/users/ — create a staff member
    """

    permission_classes = [IsStoreManager]

    def get(self, request):
        from apps.users.models import User

        staff_roles = [
            User.Role.STORE_OWNER,
            User.Role.STORE_MANAGER,
            "cashier",
            "waiter",
        ]

        users = User.objects.filter(
            store=request.store,
            role__in=staff_roles,
        ).order_by("-date_joined")

        data = []
        for u in users:
            data.append({
                "id": str(u.id),
                "email": u.email,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "role": u.role,
                "is_active": u.is_active,
                "last_login": u.last_login.isoformat() if u.last_login else None,
            })

        return Response({
            "data": data,
            "meta": {"count": len(data)},
        })

    def post(self, request):
        from apps.users.models import User

        email = request.data.get("email", "").strip()
        first_name = request.data.get("first_name", "").strip()
        last_name = request.data.get("last_name", "").strip()
        role = request.data.get("role", "cashier")
        password = request.data.get("password", "")

        if not email or not password:
            return Response(
                {"errors": [{"field": "email", "message": "Email and password required", "code": "REQUIRED"}]},
                status=400,
            )

        if User.objects.filter(email=email, store=request.store).exists():
            return Response(
                {"errors": [{"field": "email", "message": "User already exists", "code": "DUPLICATE"}]},
                status=400,
            )

        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
            store=request.store,
            is_active=True,
        )
        user.set_password(password)
        user.save()

        return Response({
            "data": {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
                "is_active": user.is_active,
                "last_login": None,
            }
        }, status=201)
