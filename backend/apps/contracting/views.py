"""
Contracting views.

Stories 6.1-6.6.
"""

import io
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.http import FileResponse, Http404
from django.utils import timezone

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pagination import StoreCursorPagination
from core.permissions import HasStore, IsStoreManager


class _ServicePagination(StoreCursorPagination):
    ordering = "name"

from apps.contracting.models import (
    AvailabilitySlot,
    Invoice,
    Job,
    JobMilestone,
    Quote,
    QuoteRequest,
    Service,
    ServiceBooking,
    _generate_invoice_token,
    _verify_invoice_token,
)
from apps.contracting.serializers import (
    AvailabilitySlotSerializer,
    InvoiceSerializer,
    JobMilestoneSerializer,
    JobSerializer,
    QuoteRequestSerializer,
    QuoteSerializer,
    ServiceBookingSerializer,
    ServiceSerializer,
)
from apps.contracting.tasks import generate_invoice_pdf, send_booking_confirmation
from core.pagination import StoreCursorPagination


def _compress_to_webp(image_file, max_kb=800):
    """Compress uploaded image to WebP ≤ max_kb KB."""
    from PIL import Image

    img = Image.open(image_file)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")

    for quality in (85, 75, 65, 50, 35, 20):
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=quality)
        if buf.tell() <= max_kb * 1024:
            buf.seek(0)
            return buf
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Story 6.1 — Service catalog
# ---------------------------------------------------------------------------


class ServiceListView(APIView):
    """
    GET  /api/v1/contracting/services/ — list active services (public)
    POST /api/v1/contracting/services/ — create service (auth)
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsStoreManager()]

    def get(self, request):
        services = Service.objects.filter(store=request.store, is_active=True)
        paginator = _ServicePagination()
        page = paginator.paginate_queryset(services, request)
        return paginator.get_paginated_response(ServiceSerializer(page, many=True).data)

    def post(self, request):
        serializer = ServiceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = Service.objects.create(store=request.store, **serializer.validated_data)
        return Response(ServiceSerializer(service).data, status=201)


class ServiceDetailView(APIView):
    """GET /api/v1/contracting/services/{id}/ — service detail."""

    permission_classes = [AllowAny]

    def get(self, request, service_id):
        try:
            service = Service.objects.get(id=service_id, store=request.store)
        except Service.DoesNotExist:
            return Response(status=404)
        return Response(ServiceSerializer(service).data)


class ServiceAvailabilityView(APIView):
    """
    GET /api/v1/contracting/services/{service_id}/availability/

    Returns available (not booked) slots for the next 30 days.
    """

    permission_classes = [AllowAny]

    def get(self, request, service_id):
        try:
            service = Service.objects.get(id=service_id, store=request.store)
        except Service.DoesNotExist:
            return Response(status=404)

        cutoff = timezone.now() + timedelta(days=30)
        slots = AvailabilitySlot.objects.filter(
            store=request.store,
            service=service,
            is_booked=False,
            start_time__gte=timezone.now(),
            start_time__lte=cutoff,
        )
        return Response(AvailabilitySlotSerializer(slots, many=True).data)


# ---------------------------------------------------------------------------
# Story 6.2 — Bookings
# ---------------------------------------------------------------------------


class BookingListView(APIView):
    """
    GET  /api/v1/contracting/bookings/ — list bookings for this store
    POST /api/v1/contracting/bookings/ — create a booking
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsStoreManager()]

    def get(self, request):
        bookings = ServiceBooking.objects.filter(store=request.store)
        return Response(ServiceBookingSerializer(bookings, many=True).data)

    def post(self, request):
        serializer = ServiceBookingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        slot_id = request.data.get("slot_id")
        if not slot_id:
            return Response({"code": "SLOT_REQUIRED"}, status=400)

        try:
            with transaction.atomic():
                slot = AvailabilitySlot.objects.select_for_update().get(
                    id=slot_id, store=request.store, is_booked=False
                )
                slot.is_booked = True
                slot.save(update_fields=["is_booked"])

                booking = ServiceBooking.objects.create(
                    store=request.store,
                    service=slot.service,
                    slot=slot,
                    customer_phone=data["customer_phone"],
                    customer_name=data.get("customer_name", ""),
                    notes=data.get("notes", ""),
                )
        except AvailabilitySlot.DoesNotExist:
            return Response(
                {"code": "SLOT_UNAVAILABLE", "detail": "Slot not found or already booked."},
                status=409,
            )

        return Response(ServiceBookingSerializer(booking).data, status=201)


class BookingConfirmView(APIView):
    """PATCH /api/v1/contracting/bookings/{id}/confirm/"""

    permission_classes = [IsStoreManager]

    def patch(self, request, booking_id):
        try:
            booking = ServiceBooking.objects.get(id=booking_id, store=request.store)
        except ServiceBooking.DoesNotExist:
            return Response(status=404)

        if booking.status != ServiceBooking.STATUS_PENDING:
            return Response(
                {"code": "BOOKING_NOT_PENDING", "detail": "Booking must be PENDING to confirm."},
                status=422,
            )

        booking.status = ServiceBooking.STATUS_CONFIRMED
        booking.save(update_fields=["status"])

        # Dispatch confirmation notification
        send_booking_confirmation.delay(str(booking.id))

        return Response(ServiceBookingSerializer(booking).data)


# ---------------------------------------------------------------------------
# Story 6.3 — Quote Request → Quote
# ---------------------------------------------------------------------------


class QuoteRequestListView(APIView):
    """
    GET  /api/v1/contracting/quote-requests/ — list (staff)
    POST /api/v1/contracting/quote-requests/ — create (customer submits)
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsStoreManager()]
        return [IsAuthenticated()]

    def get(self, request):
        qrs = QuoteRequest.objects.filter(store=request.store)
        return Response(QuoteRequestSerializer(qrs, many=True).data)

    def post(self, request):
        serializer = QuoteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        qr = QuoteRequest.objects.create(store=request.store, **data)
        return Response(QuoteRequestSerializer(qr).data, status=201)


class CreateQuoteView(APIView):
    """POST /api/v1/contracting/quote-requests/{id}/quote/"""

    permission_classes = [IsStoreManager]

    def post(self, request, quote_request_id):
        try:
            qr = QuoteRequest.objects.get(
                id=quote_request_id, store=request.store, status=QuoteRequest.STATUS_OPEN
            )
        except QuoteRequest.DoesNotExist:
            return Response(status=404)

        serializer = QuoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            quote = Quote.objects.create(
                store=request.store,
                quote_request=qr,
                **data,
            )
            qr.status = QuoteRequest.STATUS_QUOTED
            qr.save(update_fields=["status"])

        return Response(QuoteSerializer(quote).data, status=201)


class QuoteAcceptView(APIView):
    """PATCH /api/v1/contracting/quotes/{id}/accept/"""

    permission_classes = [IsStoreManager]

    def patch(self, request, quote_id):
        try:
            quote = Quote.objects.select_related("quote_request").get(
                id=quote_id, store=request.store, status=Quote.STATUS_QUOTED
            )
        except Quote.DoesNotExist:
            return Response(status=404)

        with transaction.atomic():
            quote.status = Quote.STATUS_ACCEPTED
            quote.save(update_fields=["status"])

            quote.quote_request.status = QuoteRequest.STATUS_CLOSED
            quote.quote_request.save(update_fields=["status"])

            # Auto-create Job from accepted quote
            job = Job.objects.create(
                store=request.store,
                quote=quote,
                title=f"Job: {quote.quote_request.description[:100]}",
                description=quote.quote_request.description,
            )

        return Response(
            {"quote_id": str(quote.id), "job_id": str(job.id), "status": quote.status}
        )


class QuoteRejectView(APIView):
    """PATCH /api/v1/contracting/quotes/{id}/reject/"""

    permission_classes = [IsStoreManager]

    def patch(self, request, quote_id):
        try:
            quote = Quote.objects.select_related("quote_request").get(
                id=quote_id, store=request.store, status=Quote.STATUS_QUOTED
            )
        except Quote.DoesNotExist:
            return Response(status=404)

        with transaction.atomic():
            quote.status = Quote.STATUS_REJECTED
            quote.save(update_fields=["status"])
            quote.quote_request.status = QuoteRequest.STATUS_CLOSED
            quote.quote_request.save(update_fields=["status"])

        return Response({"quote_id": str(quote.id), "status": quote.status})


# ---------------------------------------------------------------------------
# Story 6.4 — Job + Milestones + Completion Photos
# ---------------------------------------------------------------------------


class JobDetailView(APIView):
    """GET /api/v1/contracting/jobs/{id}/"""

    permission_classes = [HasStore]

    def get(self, request, job_id):
        try:
            job = Job.objects.prefetch_related("milestones").get(
                id=job_id, store=request.store
            )
        except Job.DoesNotExist:
            return Response(status=404)
        return Response(JobSerializer(job).data)


class JobTransitionView(APIView):
    """PATCH /api/v1/contracting/jobs/{id}/transition/"""

    permission_classes = [IsStoreManager]

    def patch(self, request, job_id):
        try:
            job = Job.objects.get(id=job_id, store=request.store)
        except Job.DoesNotExist:
            return Response(status=404)

        new_status = request.data.get("status", "")
        try:
            job.transition(new_status)
        except ValueError as exc:
            return Response({"code": "INVALID_JOB_TRANSITION", "detail": str(exc)}, status=422)

        return Response({"job_id": str(job.id), "status": job.status})


class MilestoneUpdateView(APIView):
    """PATCH /api/v1/contracting/milestones/{id}/"""

    permission_classes = [IsStoreManager]

    def patch(self, request, milestone_id):
        try:
            milestone = JobMilestone.objects.get(
                id=milestone_id, job__store=request.store
            )
        except JobMilestone.DoesNotExist:
            return Response(status=404)

        update_fields = []

        if "notes" in request.data:
            milestone.notes = request.data["notes"]
            update_fields.append("notes")

        # Completion photo — compress to WebP
        photo = request.FILES.get("completion_photo")
        if photo:
            from django.core.files.base import ContentFile
            from django.utils.text import slugify

            webp_buf = _compress_to_webp(photo)
            filename = f"{milestone.id}.webp"
            milestone.completion_photo.save(filename, ContentFile(webp_buf.read()), save=False)
            update_fields.append("completion_photo")

            milestone.status = JobMilestone.STATUS_COMPLETED
            milestone.completed_at = timezone.now()
            update_fields += ["status", "completed_at"]

        if update_fields:
            milestone.save(update_fields=update_fields)

        return Response(JobMilestoneSerializer(milestone).data)


# ---------------------------------------------------------------------------
# Story 6.5 — Invoice + PDF
# ---------------------------------------------------------------------------


class CreateInvoiceView(APIView):
    """POST /api/v1/contracting/jobs/{job_id}/invoice/"""

    permission_classes = [IsStoreManager]

    def post(self, request, job_id):
        try:
            job = Job.objects.get(id=job_id, store=request.store)
        except Job.DoesNotExist:
            return Response(status=404)

        if job.status != Job.STATUS_COMPLETED:
            return Response(
                {"code": "JOB_NOT_COMPLETED", "detail": "Job must be COMPLETED to generate invoice."},
                status=422,
            )

        if hasattr(job, "invoice"):
            return Response(
                {"code": "INVOICE_EXISTS", "detail": "Invoice already exists for this job."},
                status=409,
            )

        # Build line items from job source
        if hasattr(job, "quote") and job.quote:
            line_items = job.quote.line_items
            total_amount = job.quote.total_amount
        else:
            # Build from job description
            line_items = [{"description": job.title, "quantity": 1, "unit_price": str(0)}]
            total_amount = Decimal("0.00")

        with transaction.atomic():
            invoice = Invoice.objects.create(
                store=request.store,
                job=job,
                line_items=line_items,
                total_amount=total_amount,
            )
            # Generate HMAC token for shareable URL
            invoice.shareable_token = _generate_invoice_token(str(invoice.id))
            invoice.save(update_fields=["shareable_token"])

        # Enqueue PDF generation
        generate_invoice_pdf.delay(str(invoice.id))

        return Response(InvoiceSerializer(invoice).data, status=201)


class InvoiceDownloadView(APIView):
    """
    GET /api/v1/contracting/invoices/{token}/download/

    Public endpoint — serves the PDF for the contractor's WhatsApp link.
    No auth required; token is HMAC-validated.
    """

    permission_classes = [AllowAny]

    def get(self, request, token):
        invoice_id = _verify_invoice_token(token)
        if not invoice_id:
            return Response({"code": "INVALID_TOKEN"}, status=403)

        try:
            invoice = Invoice.objects.get(id=invoice_id)
        except Invoice.DoesNotExist:
            return Response(status=404)

        if not invoice.pdf_file:
            return Response(
                {"code": "PDF_NOT_READY", "detail": "PDF is still being generated."},
                status=202,
            )

        return FileResponse(
            invoice.pdf_file.open("rb"),
            content_type="application/pdf",
            filename=f"invoice-{invoice.id}.pdf",
        )


# ---------------------------------------------------------------------------
# Story 6.6 — Invoice payment
# ---------------------------------------------------------------------------


class InvoicePayView(APIView):
    """
    POST /api/v1/contracting/invoices/{invoice_id}/pay/

    Initiates M-Pesa STK Push for invoice payment.
    Reference: f"invoice-{invoice.id}"
    """

    permission_classes = [HasStore]

    def post(self, request, invoice_id):
        store = request.store
        try:
            invoice = Invoice.objects.select_related("job").get(
                id=invoice_id, store=store
            )
        except Invoice.DoesNotExist:
            return Response(status=404)

        if invoice.payment_status == Invoice.PAYMENT_STATUS_PAID:
            return Response({"code": "ALREADY_PAID"}, status=409)

        phone = request.data.get("phone", "")
        if not phone:
            return Response({"code": "PHONE_REQUIRED"}, status=400)

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
                amount=invoice.total_amount,
                phone=phone,
                reference=f"invoice-{invoice.id}",
            )
        except InvalidPhoneNumberError as exc:
            return Response({"code": "INVALID_PHONE_NUMBER", "detail": str(exc)}, status=422)
        except StkPushRateLimitedError as exc:
            return Response(
                {"code": "STK_PUSH_RATE_LIMITED", "retry_after": exc.retry_after.isoformat()},
                status=429,
            )
        except StkPushInitiationError:
            return Response({"code": "PAYMENT_GATEWAY_ERROR"}, status=502)

        return Response(
            {
                "transaction_id": str(txn.id),
                "status": txn.status,
                "customer_message": "Payment request sent to your phone.",
            }
        )
