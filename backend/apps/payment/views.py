"""Payment views.

Implementation: Story 2.2, Story 2.3, Story 2.5, Story 4.7
"""

import hashlib
import hmac

import structlog
from django.conf import settings

from rest_framework.permissions import AllowAny, IsAuthenticated

log = structlog.get_logger(__name__)
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payment.exceptions import (
    InvalidPhoneNumberError,
    StkPushInitiationError,
    StkPushRateLimitedError,
)
from apps.payment.models import MpesaTransaction, MpesaTransactionStatus
from apps.payment.serializers import InitiateStkPushSerializer
from apps.payment.services import initiate_payment
from apps.payment.tasks import initiate_reversal, process_mpesa_callback


class InitiateStkPushView(APIView):
    """POST /api/v1/payments/initiate-stk/

    Initiates an M-Pesa STK Push for a customer checkout.
    Requires authentication. Store is resolved from request.store
    (set by TenantMiddleware — never looked up manually in the view).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = InitiateStkPushSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            txn = initiate_payment(
                store=request.store,
                method=data["method"],
                amount=data["amount"],
                phone=data["phone"],
                reference=data["reference"],
            )
        except InvalidPhoneNumberError as exc:
            return Response(
                {"code": "INVALID_PHONE_NUMBER", "detail": str(exc)},
                status=422,
            )
        except StkPushRateLimitedError as exc:
            return Response(
                {
                    "code": "STK_PUSH_RATE_LIMITED",
                    "retry_after": exc.retry_after.isoformat(),
                },
                status=429,
            )
        except StkPushInitiationError:
            return Response(
                {
                    "code": "PAYMENT_GATEWAY_ERROR",
                    "detail": "STK push could not be initiated",
                },
                status=502,
            )

        return Response(
            {
                "transaction_id": str(txn.id),
                "status": txn.status,
                "customer_message": "Payment request sent to your phone.",
            },
            status=200,
        )


def _verify_daraja_signature(request) -> bool:
    """Return True if X-Daraja-Signature header matches the payload HMAC."""
    expected_sig = request.META.get("HTTP_X_DARAJA_SIGNATURE", "")
    secret = getattr(settings, "MPESA_WEBHOOK_SECRET", "")
    if not secret:
        log.error("mpesa_webhook_secret_not_configured")
        return False
    raw_body = request.body  # bytes — must be read before DRF parses JSON
    computed = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, expected_sig)


class MpesaCallbackView(APIView):
    """POST /api/v1/payments/mpesa-callback/

    Public webhook endpoint for Daraja STK Push callbacks.
    Validates HMAC signature, then enqueues async processing.
    Returns HTTP 200 immediately — Daraja retries on non-200.
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # no auth for public webhook

    def post(self, request):
        # Signature check must come before request.data is accessed
        if not _verify_daraja_signature(request):
            return Response(
                {
                    "code": "INVALID_SIGNATURE",
                    "detail": "Webhook signature verification failed",
                },
                status=400,
            )

        process_mpesa_callback.delay(request.data)
        return Response({"status": "accepted"}, status=200)


class ReversePaymentView(APIView):
    """POST /api/v1/payments/{transaction_id}/reverse/

    Queues an M-Pesa reversal for a confirmed payment.
    Returns HTTP 202 immediately — reversal is processed asynchronously.
    Requires authentication. Store scoping enforced via request.store.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, transaction_id):
        reason = request.data.get("reason", "")
        if not reason:
            return Response(
                {"code": "REASON_REQUIRED", "detail": "reason is required"},
                status=400,
            )

        try:
            txn = MpesaTransaction.objects.get(
                id=transaction_id, store=request.store
            )
        except MpesaTransaction.DoesNotExist:
            return Response(status=404)

        if txn.status != MpesaTransactionStatus.CONFIRMED:
            return Response(
                {
                    "code": "REVERSAL_NOT_ALLOWED",
                    "detail": (
                        f"Cannot reverse transaction with status {txn.status!r}"
                    ),
                },
                status=422,
            )

        initiate_reversal.delay(
            transaction_id=str(txn.id), reason=reason
        )
        return Response(
            {"status": "reversal_queued", "transaction_id": str(txn.id)},
            status=202,
        )


class CardPaymentScaffoldView(APIView):
    """
    Story 4.7 — Card payment scaffold (Stripe + Flutterwave).

    POST /api/v1/payments/card/initiate/
    Body: {"provider": "stripe" | "flutterwave", ...}

    Returns HTTP 501 — card payments are scaffolded but not yet live.
    Endpoints appear in OpenAPI schema with 501 response documented.
    Activation requires only provider implementation, no URL changes.
    """

    def post(self, request):
        provider = request.data.get("provider", "").lower()
        if provider not in ("stripe", "flutterwave"):
            return Response(
                {"errors": [{"code": "INVALID_PROVIDER", "message": "Use 'stripe' or 'flutterwave'."}]},
                status=400,
            )
        return Response(
            {"detail": "CARD_PAYMENT_NOT_LIVE"},
            status=501,
        )
