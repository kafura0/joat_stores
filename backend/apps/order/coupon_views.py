"""
Coupon views — Story 4.5.

Admin CRUD + storefront validate endpoint.
"""

from decimal import Decimal

from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pagination import StoreCursorPagination
from core.permissions import IsStoreManager


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = __import__("apps.order.coupons", fromlist=["Coupon"]).Coupon
        fields = [
            "id",
            "code",
            "description",
            "discount_type",
            "discount_value",
            "min_order_amount",
            "max_discount_amount",
            "max_uses",
            "times_used",
            "max_uses_per_customer",
            "valid_from",
            "valid_to",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "times_used", "created_at"]


class CouponListView(APIView):
    """
    GET  /api/v1/store/coupons/          — list coupons (paginated)
    POST /api/v1/store/coupons/          — create coupon
    """

    permission_classes = [IsStoreManager]

    def get(self, request):
        from apps.order.coupons import Coupon

        coupons = Coupon.objects.filter(store=request.store).order_by("-created_at")

        page = request.query_params.get("page")
        paginator = StoreCursorPagination()
        page = paginator.paginate_queryset(coupons, request)
        serializer = CouponSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        from apps.order.coupons import Coupon

        serializer = CouponSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"errors": serializer.errors}, status=400)

        # Check unique code per store
        code = serializer.validated_data["code"].upper()
        if Coupon.objects.filter(store=request.store, code=code).exists():
            return Response(
                {"errors": [{"code": "DUPLICATE_CODE", "message": "A coupon with this code already exists."}]},
                status=400,
            )

        coupon = Coupon.objects.create(
            store=request.store,
            code=code,
            **{k: v for k, v in serializer.validated_data.items() if k != "code"},
        )
        return Response(CouponSerializer(coupon).data, status=201)


class CouponDetailView(APIView):
    """
    GET    /api/v1/store/coupons/{id}/
    PATCH  /api/v1/store/coupons/{id}/
    DELETE /api/v1/store/coupons/{id}/
    """

    permission_classes = [IsStoreManager]

    def get(self, request, coupon_id):
        from apps.order.coupons import Coupon

        try:
            coupon = Coupon.objects.get(id=coupon_id, store=request.store)
        except Coupon.DoesNotExist:
            return Response(status=404)
        return Response(CouponSerializer(coupon).data)

    def patch(self, request, coupon_id):
        from apps.order.coupons import Coupon

        try:
            coupon = Coupon.objects.get(id=coupon_id, store=request.store)
        except Coupon.DoesNotExist:
            return Response(status=404)

        serializer = CouponSerializer(coupon, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({"errors": serializer.errors}, status=400)

        for key, value in serializer.validated_data.items():
            setattr(coupon, key, value)
        coupon.save()
        return Response(CouponSerializer(coupon).data)

    def delete(self, request, coupon_id):
        from apps.order.coupons import Coupon

        try:
            coupon = Coupon.objects.get(id=coupon_id, store=request.store)
        except Coupon.DoesNotExist:
            return Response(status=404)
        coupon.delete()
        return Response(status=204)


class CouponValidateView(APIView):
    """
    POST /api/v1/store/coupons/validate/

    Storefront endpoint — validates a coupon code and returns discount info
    without applying it. Used for the "Apply" button in the checkout UI.

    Body: {code, subtotal}
    """

    permission_classes = []

    def post(self, request):
        from apps.order.coupons import Coupon

        code = request.data.get("code", "").strip()
        if not code:
            return Response(
                {"errors": [{"code": "CODE_REQUIRED", "message": "Coupon code is required."}]},
                status=400,
            )

        try:
            coupon = Coupon.objects.get(
                store=request.store,
                code__iexact=code,
            )
        except Coupon.DoesNotExist:
            return Response(
                {"valid": False, "message": "Invalid coupon code."},
                status=404,
            )

        if not coupon.is_valid:
            return Response(
                {"valid": False, "message": "This coupon is no longer valid."},
                status=200,
            )

        subtotal = Decimal(str(request.data.get("subtotal", "0")))
        discount = coupon.calculate_discount(subtotal)

        if discount <= 0:
            return Response(
                {
                    "valid": False,
                    "message": f"Minimum order amount: KES {coupon.min_order_amount}",
                },
                status=200,
            )

        return Response({
            "valid": True,
            "code": coupon.code,
            "discount_type": coupon.discount_type,
            "discount_value": str(coupon.discount_value),
            "discount_amount": str(discount),
            "message": f"KES {discount} discount applied!",
        })
