"""Payment views.

Implementation: Story 2.2, Story 2.3, Story 2.5, Story 2.6, Story 4.7
"""

import hashlib
import hmac

import structlog
from django.conf import settings

from rest_framework.permissions import AllowAny, IsAuthenticated

from core.permissions import IsStoreManager, IsStoreScoped

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


class C2BCallbackView(APIView):
    """POST /api/v1/payments/c2b-callback/

    Public webhook endpoint for Daraja C2B (customer-initiated) payments.
    Customer pays to till number → Safaricom POSTs here → we match to order.

    C2B payload format:
    {
        "TransactionType": "Paybill",
        "TransID": "QHK71G4YS0",
        "TransTime": "20230930143022",
        "TransAmount": "1000",
        "BusinessShortCode": "174379",
        "BillRefNumber": "ORDER-abc123",
        "InvoiceNumber": "",
        "OrgAccountBalance": "12345",
        "ThirdPartyTransID": "",
        "MSISDN": "254712345678",
        "FirstName": "John",
        "MiddleName": "",
        "LastName": "Doe"
    }
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        from apps.payment.tasks import process_c2b_callback

        log.info("c2b_callback_received", data_keys=list(request.data.keys()))
        process_c2b_callback.delay(request.data)
        return Response({"status": "accepted"}, status=200)


class C2BRegisterView(APIView):
    """POST /api/v1/payments/c2b-register/

    Register C2B callback URLs with Safaricom for the store's till number.
    Requires store owner/manager. Only needs to be done once per till.
    """

    permission_classes = [IsStoreManager]

    def post(self, request):
        from apps.payment.daraja import get_daraja_client
        from django.conf import settings

        base_url = f"https://{request.get_host()}"
        confirmation_url = f"{base_url}/api/v1/payments/c2b-callback/"
        validation_url = f"{base_url}/api/v1/payments/c2b-validation/"

        try:
            client = get_daraja_client()
            result = client.register_c2b_url(confirmation_url, validation_url)
            return Response({"data": result}, status=200)
        except Exception as exc:
            log.error("c2b_register_failed", error=str(exc))
            return Response(
                {"errors": [{"code": "C2B_REGISTER_FAILED", "message": str(exc)}]},
                status=502,
            )


class C2BValidationView(APIView):
    """POST /api/v1/payments/c2b-validation/

    Pre-validation endpoint for C2B payments. Safaricom calls this first
    to check if the payment should be accepted. Always returns 200 OK
    to accept all payments.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        log.info("c2b_validation", data=request.data)
        return Response({"ResultCode": 0, "ResultDesc": "Accepted"}, status=200)


class ReversePaymentView(APIView):
    """POST /api/v1/payments/{transaction_id}/reverse/

    Queues an M-Pesa reversal for a confirmed payment.
    Returns HTTP 202 immediately — reversal is processed asynchronously.
    Requires authentication. Store scoping enforced via request.store.
    """

    permission_classes = [IsStoreManager]

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


class CardPaymentInitiateView(APIView):
    """
    POST /api/v1/payments/card/initiate/

    Story 2.6 — Initiate a Stripe card payment.
    Body: {"provider": "stripe", "amount": "1500.00", "reference": "ORD-123", "customer_email": "..."}

    Returns a client_secret for the storefront to complete payment via
    Stripe Elements / PaymentElement.
    """

    permission_classes = [IsStoreScoped]

    def post(self, request):
        provider = request.data.get("provider", "").lower()
        if provider not in ("stripe",):
            return Response(
                {"errors": [{"code": "INVALID_PROVIDER", "message": "Use 'stripe'."}]},
                status=400,
            )

        amount = request.data.get("amount")
        reference = request.data.get("reference", "")
        customer_email = request.data.get("customer_email", "")

        if not amount:
            return Response(
                {"errors": [{"code": "AMOUNT_REQUIRED", "message": "amount is required"}]},
                status=400,
            )
        if not reference:
            return Response(
                {"errors": [{"code": "REFERENCE_REQUIRED", "message": "reference is required"}]},
                status=400,
            )

        from apps.payment.services import initiate_card_payment

        try:
            result = initiate_card_payment(
                store=request.store,
                amount=amount,
                reference=reference,
                provider=provider,
                customer_email=customer_email,
            )
        except ValueError as exc:
            return Response(
                {"errors": [{"code": "CARD_PAYMENT_ERROR", "message": str(exc)}]},
                status=400,
            )
        except Exception as exc:
            log.exception("card_payment_initiation_error", reference=reference)
            return Response(
                {"errors": [{"code": "PAYMENT_GATEWAY_ERROR", "message": "Card payment could not be initiated."}]},
                status=502,
            )

        return Response(result, status=200)


class StripeWebhookView(APIView):
    """
    POST /api/v1/payments/stripe-webhook/

    Stripe webhook endpoint for PaymentIntent events.
    Validates signature, then updates CardTransaction status.
    Returns HTTP 200 immediately.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        from django.conf import settings

        import stripe as stripe_lib
        stripe_lib.api_key = settings.STRIPE_SECRET_KEY

        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

        try:
            event = stripe_lib.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            return Response({"error": "Invalid payload"}, status=400)
        except stripe_lib.error.SignatureVerificationError:
            return Response({"error": "Invalid signature"}, status=400)

        from apps.payment.models import CardTransaction, CardTransactionStatus

        if event["type"] == "payment_intent.succeeded":
            intent = event["data"]["object"]
            _update_card_txn(intent["id"], CardTransactionStatus.SUCCEEDED)
            log.info("stripe_payment_succeeded", payment_intent_id=intent["id"])

        elif event["type"] == "payment_intent.payment_failed":
            intent = event["data"]["object"]
            reason = intent.get("last_payment_error", {}).get("message", "")
            _update_card_txn(
                intent["id"],
                CardTransactionStatus.FAILED,
                failure_reason=reason,
            )
            log.info("stripe_payment_failed", payment_intent_id=intent["id"], reason=reason)

        elif event["type"] == "payment_intent.processing":
            intent = event["data"]["object"]
            _update_card_txn(intent["id"], CardTransactionStatus.PROCESSING)

        return Response({"status": "ok"})


def _update_card_txn(payment_intent_id: str, status, failure_reason: str = "") -> None:
    """Update a CardTransaction status by Stripe PaymentIntent ID."""
    from django.utils import timezone

    from apps.payment.models import CardTransaction, CardTransactionStatus

    try:
        txn = CardTransaction.objects.get(stripe_payment_intent_id=payment_intent_id)
        txn.status = status
        if status == CardTransactionStatus.SUCCEEDED:
            txn.completed_at = timezone.now()
        if failure_reason:
            txn.failure_reason = failure_reason
        txn.save(update_fields=["status", "completed_at", "failure_reason"])
    except CardTransaction.DoesNotExist:
        log.warning("card_txn_not_found_for_intent", payment_intent_id=payment_intent_id)
