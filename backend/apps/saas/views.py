"""
SaaS views — Epic 9.

Story 9.1: Plan list (public) + create (platform admin)
Story 9.2: StoreSubscription read / platform status override
Story 9.3: POST /renew/ — initiates M-Pesa STK Push for renewal
Story 9.4: Plan limit info endpoint
"""

import structlog
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsStoreManager

from apps.saas.models import (
    InvalidSubscriptionTransition,
    Plan,
    StoreSubscription,
    SubscriptionStatus,
)
from apps.saas.serializers import PlanSerializer, StoreSubscriptionSerializer

log = structlog.get_logger(__name__)


def _is_platform_admin(user) -> bool:
    return getattr(user, "role", None) == "platform_admin"


# ---------------------------------------------------------------------------
# 9.1 — Plans
# ---------------------------------------------------------------------------


class PlanListView(APIView):
    """
    GET  /api/v1/saas/plans/  — list active public plans (any auth)
    POST /api/v1/saas/plans/  — create plan (platform admin)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Plan.objects.filter(is_active=True)
        if not _is_platform_admin(request.user):
            qs = qs.filter(is_public=True)
        return Response(PlanSerializer(qs, many=True).data)

    def post(self, request):
        if not _is_platform_admin(request.user):
            return Response(
                {"errors": [{"code": "PERMISSION_DENIED", "message": "Platform admin only."}]},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = PlanSerializer(data=request.data)
        if serializer.is_valid():
            plan = serializer.save()
            return Response(PlanSerializer(plan).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PlanDetailView(APIView):
    """GET /api/v1/saas/plans/{id}/ — plan detail"""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            plan = Plan.objects.get(pk=pk, is_active=True)
        except Plan.DoesNotExist:
            return Response(
                {"errors": [{"code": "NOT_FOUND", "message": "Plan not found."}]},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(PlanSerializer(plan).data)


# ---------------------------------------------------------------------------
# 9.2 — StoreSubscription (store owner view)
# ---------------------------------------------------------------------------


class SubscriptionView(APIView):
    """
    GET /api/v1/saas/subscription/
    Returns the current store's subscription and plan details.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        store = request.store
        try:
            sub = StoreSubscription.objects.select_related("plan").get(store=store)
        except StoreSubscription.DoesNotExist:
            return Response(
                {"errors": [{"code": "NOT_FOUND", "message": "No subscription found for this store."}]},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(StoreSubscriptionSerializer(sub).data)


# ---------------------------------------------------------------------------
# 9.3 — M-Pesa subscription renewal
# ---------------------------------------------------------------------------


class SubscriptionRenewView(APIView):
    """
    POST /api/v1/saas/subscription/renew/

    Initiates an M-Pesa STK Push for the current plan renewal amount.
    The payment reference is "subscription-{store_id}" — handled in apps.py signal.
    """

    permission_classes = [IsStoreManager]

    def post(self, request):
        store = request.store
        try:
            sub = StoreSubscription.objects.select_related("plan").get(store=store)
        except StoreSubscription.DoesNotExist:
            return Response(
                {"errors": [{"code": "NOT_FOUND", "message": "No subscription found."}]},
                status=status.HTTP_404_NOT_FOUND,
            )

        if sub.renewal_amount_kes <= 0:
            return Response(
                {"errors": [{"code": "FREE_PLAN", "message": "No renewal required for free plan."}]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        phone = request.data.get("phone") or getattr(request.user, "phone", None)
        if not phone:
            return Response(
                {"errors": [{"code": "PHONE_REQUIRED", "message": "Phone number is required for renewal."}]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.payment.services import initiate_payment
        from apps.payment.exceptions import (
            InvalidPhoneNumberError,
            StkPushInitiationError,
            StkPushRateLimitedError,
        )

        reference = f"subscription-{store.id}"
        try:
            tx = initiate_payment(
                store=store,
                method="mpesa",
                amount=sub.renewal_amount_kes,
                phone=phone,
                reference=reference,
            )
            log.info("subscription_renewal_initiated", store_id=str(store.id), tx_id=str(tx.id))
            return Response(
                {
                    "message": "STK Push sent. Complete the M-Pesa prompt on your phone.",
                    "transaction_id": str(tx.id),
                    "amount_kes": str(sub.renewal_amount_kes),
                },
                status=status.HTTP_202_ACCEPTED,
            )
        except InvalidPhoneNumberError as exc:
            return Response(
                {"errors": [{"code": "INVALID_PHONE", "message": str(exc)}]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except StkPushRateLimitedError as exc:
            return Response(
                {"errors": [{"code": "RATE_LIMITED", "message": str(exc)}]},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except StkPushInitiationError as exc:
            return Response(
                {"errors": [{"code": "STK_PUSH_FAILED", "message": str(exc)}]},
                status=status.HTTP_502_BAD_GATEWAY,
            )


# ---------------------------------------------------------------------------
# Platform admin — subscription management
# ---------------------------------------------------------------------------


class PlatformSubscriptionListView(APIView):
    """
    GET /api/v1/platform/subscriptions/ — list all subscriptions (platform admin)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_platform_admin(request.user):
            return Response(
                {"errors": [{"code": "PERMISSION_DENIED", "message": "Platform admin only."}]},
                status=status.HTTP_403_FORBIDDEN,
            )
        qs = StoreSubscription.objects.select_related("plan", "store").order_by("-created_at")

        # Optional filters
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        return Response(StoreSubscriptionSerializer(qs, many=True).data)


class PlatformSubscriptionDetailView(APIView):
    """
    GET   /api/v1/platform/subscriptions/{id}/  — get subscription
    PATCH /api/v1/platform/subscriptions/{id}/  — transition status or assign plan
    """

    permission_classes = [IsAuthenticated]

    def _get_sub(self, pk):
        try:
            return StoreSubscription.objects.select_related("plan", "store").get(pk=pk)
        except StoreSubscription.DoesNotExist:
            return None

    def get(self, request, pk):
        if not _is_platform_admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        sub = self._get_sub(pk)
        if sub is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(StoreSubscriptionSerializer(sub).data)

    def patch(self, request, pk):
        if not _is_platform_admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        sub = self._get_sub(pk)
        if sub is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get("status")
        plan_id = request.data.get("plan_id")

        if new_status:
            try:
                sub.transition_status(new_status)
            except InvalidSubscriptionTransition as exc:
                return Response(
                    {"errors": [{"code": "INVALID_TRANSITION", "message": str(exc)}]},
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )

        if plan_id is not None:
            try:
                plan = Plan.objects.get(pk=plan_id, is_active=True)
                sub.plan = plan
                sub.save(update_fields=["plan", "updated_at"])
            except Plan.DoesNotExist:
                return Response(
                    {"errors": [{"code": "NOT_FOUND", "message": f"Plan {plan_id} not found."}]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(StoreSubscriptionSerializer(sub).data)
