"""
Loyalty views — Epic 10.

Story 10.1: GET /api/v1/loyalty/account/  — points balance
            GET /api/v1/loyalty/history/  — points ledger
            POST /api/v1/loyalty/redeem/  — redeem points
Story 10.2: GET  /api/v1/loyalty/stamp-cards/         — store's stamp cards
            POST /api/v1/loyalty/stamp-cards/          — create card (owner)
            GET  /api/v1/loyalty/my-stamp-cards/       — customer's progress
Story 10.4: GET  /api/v1/loyalty/customers/            — customer profiles (owner)
            GET  /api/v1/loyalty/customers/{phone}/    — single profile
"""

import structlog
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.loyalty.models import (
    CustomerProfile,
    CustomerStampCard,
    LoyaltyAccount,
    StampCard,
)
from apps.loyalty.serializers import (
    CustomerProfileSerializer,
    CustomerStampCardSerializer,
    LoyaltyAccountSerializer,
    PointsTransactionSerializer,
    StampCardSerializer,
)

log = structlog.get_logger(__name__)


def _is_store_staff(user) -> bool:
    return getattr(user, "role", None) in ("store_owner", "store_manager", "platform_admin")


# ---------------------------------------------------------------------------
# 10.1 — Points balance + history + redemption
# ---------------------------------------------------------------------------


class LoyaltyAccountView(APIView):
    """GET /api/v1/loyalty/account/?phone=+254XXXXXXXXX"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        phone = request.query_params.get("phone") or getattr(request.user, "phone", None)
        if not phone:
            return Response(
                {"errors": [{"code": "PHONE_REQUIRED", "message": "Provide ?phone= param."}]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            account = LoyaltyAccount.objects.get(store=request.store, customer_phone=phone)
        except LoyaltyAccount.DoesNotExist:
            return Response(
                {"errors": [{"code": "NOT_FOUND", "message": "No loyalty account for this phone."}]},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(LoyaltyAccountSerializer(account).data)


class PointsHistoryView(APIView):
    """GET /api/v1/loyalty/history/?phone=+254XXXXXXXXX"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        phone = request.query_params.get("phone") or getattr(request.user, "phone", None)
        if not phone:
            return Response(
                {"errors": [{"code": "PHONE_REQUIRED", "message": "Provide ?phone= param."}]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            account = LoyaltyAccount.objects.get(store=request.store, customer_phone=phone)
        except LoyaltyAccount.DoesNotExist:
            return Response([], status=status.HTTP_200_OK)
        txs = account.transactions.order_by("-occurred_at")[:50]
        return Response(PointsTransactionSerializer(txs, many=True).data)


class RedeemPointsView(APIView):
    """POST /api/v1/loyalty/redeem/ — deduct points (used at checkout)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        phone = request.data.get("phone") or getattr(request.user, "phone", None)
        points_to_redeem = request.data.get("points")
        reference = request.data.get("reference", "")

        if not phone or points_to_redeem is None:
            return Response(
                {"errors": [{"code": "INVALID_INPUT", "message": "phone and points are required."}]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            points_to_redeem = int(points_to_redeem)
        except (TypeError, ValueError):
            return Response(
                {"errors": [{"code": "INVALID_INPUT", "message": "points must be an integer."}]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            account = LoyaltyAccount.objects.select_for_update().get(
                store=request.store, customer_phone=phone
            )
            tx = account.redeem(points_to_redeem, reference=reference)
            return Response(
                {
                    "redeemed_points": points_to_redeem,
                    "new_balance": account.points_balance,
                    "transaction_id": tx.id,
                },
                status=status.HTTP_200_OK,
            )
        except LoyaltyAccount.DoesNotExist:
            return Response(
                {"errors": [{"code": "NOT_FOUND", "message": "No loyalty account for this phone."}]},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as exc:
            return Response(
                {"errors": [{"code": "INSUFFICIENT_POINTS", "message": str(exc)}]},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


# ---------------------------------------------------------------------------
# 10.2 — Stamp cards
# ---------------------------------------------------------------------------


class StampCardListView(APIView):
    """
    GET  /api/v1/loyalty/stamp-cards/ — list active stamp cards for this store
    POST /api/v1/loyalty/stamp-cards/ — create (store staff only)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        cards = StampCard.objects.filter(store=request.store, is_active=True)
        return Response(StampCardSerializer(cards, many=True).data)

    def post(self, request):
        if not _is_store_staff(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = StampCardSerializer(data=request.data)
        if serializer.is_valid():
            card = serializer.save(store=request.store)
            return Response(StampCardSerializer(card).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MyStampCardsView(APIView):
    """GET /api/v1/loyalty/my-stamp-cards/?phone=+254XXXXXXXXX"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        phone = request.query_params.get("phone") or getattr(request.user, "phone", None)
        if not phone:
            return Response(
                {"errors": [{"code": "PHONE_REQUIRED", "message": "Provide ?phone= param."}]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        cards = CustomerStampCard.objects.filter(
            store=request.store, customer_phone=phone
        ).select_related("stamp_card")
        return Response(CustomerStampCardSerializer(cards, many=True).data)


# ---------------------------------------------------------------------------
# 10.4 — Unified customer profiles
# ---------------------------------------------------------------------------


class CustomerProfileListView(APIView):
    """GET /api/v1/loyalty/customers/ — all customer profiles (store staff)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_store_staff(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        profiles = CustomerProfile.objects.filter(store=request.store).order_by("-last_order_at")[:100]
        return Response(CustomerProfileSerializer(profiles, many=True).data)


class CustomerProfileDetailView(APIView):
    """GET /api/v1/loyalty/customers/{phone}/ — single customer profile."""

    permission_classes = [IsAuthenticated]

    def get(self, request, phone):
        if not _is_store_staff(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            profile = CustomerProfile.objects.get(store=request.store, customer_phone=phone)
        except CustomerProfile.DoesNotExist:
            return Response(
                {"errors": [{"code": "NOT_FOUND", "message": "Customer profile not found."}]},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(CustomerProfileSerializer(profile).data)
