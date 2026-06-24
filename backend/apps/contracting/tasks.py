"""
Contracting Celery tasks.

Story 6.5: generate_invoice_pdf (WeasyPrint)
Story 6.2: send_booking_confirmation
"""

import logging

import structlog
from celery import shared_task
from django.utils import timezone

logger = structlog.get_logger(__name__)


@shared_task(
    bind=True,
    queue="order.notifications",
    max_retries=5,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_booking_confirmation(self, booking_id: str) -> None:
    """
    Dispatch a confirmation notification to the customer.

    TODO: Integrate WhatsApp/SMS provider (Story 10.3).
    Currently logs the confirmation only.
    """
    try:
        from apps.contracting.models import ServiceBooking

        booking = ServiceBooking.objects.select_related("service", "slot").get(id=booking_id)
        # Dispatch WhatsApp notification
        from apps.notifications.tasks import send_whatsapp_notification

        msg = (
            f"Booking confirmed for {booking.service.name} at "
            f"{booking.slot.start_time.strftime('%d %b %Y, %H:%M')}. "
            f"Reference: {booking.id}"
        )
        send_whatsapp_notification.delay(
            store_id=str(booking.store_id),
            recipient_phone=booking.customer_phone,
            message_body=msg,
            template="order_confirmation",
        )

        logger.info(
            "booking_confirmation_sent",
            booking_id=booking_id,
            customer_phone=booking.customer_phone,
        )
    except Exception as exc:
        logger.exception("send_booking_confirmation_failed", booking_id=booking_id)
        raise


@shared_task(
    bind=True,
    queue="order.notifications",
    max_retries=3,
    default_retry_delay=120,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def generate_invoice_pdf(self, invoice_id: str) -> None:
    """
    Generate a branded PDF invoice using WeasyPrint and save to MEDIA_ROOT.

    PDF includes: store logo, contractor name, line items, totals,
    payment instructions (M-Pesa shortcode).

    TODO: Implement full WeasyPrint HTML template + branding context.
    Currently generates a placeholder PDF for the scaffold.
    """
    try:
        from django.core.files.base import ContentFile

        from apps.contracting.models import Invoice

        invoice = Invoice.objects.select_related("job", "store").get(id=invoice_id)

        # --- WeasyPrint PDF generation ---
        # Full implementation requires WeasyPrint + Pillow + HTML template.
        # Scaffold: generate a minimal PDF-like placeholder.
        try:
            from weasyprint import HTML

            html_content = _build_invoice_html(invoice)
            pdf_bytes = HTML(string=html_content).write_pdf()
        except ImportError:
            # WeasyPrint not installed — create text stub
            pdf_bytes = _build_stub_pdf(invoice)

        filename = f"invoice-{invoice.id}.pdf"
        invoice.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)

        logger.info("invoice_pdf_generated", invoice_id=invoice_id, filename=filename)

    except Exception as exc:
        logger.exception("generate_invoice_pdf_failed", invoice_id=invoice_id)
        raise


def _build_invoice_html(invoice) -> str:
    """Build HTML string for WeasyPrint invoice rendering."""
    store = invoice.store
    items_html = "".join(
        f"<tr><td>{item.get('description','')}</td>"
        f"<td>{item.get('quantity', 1)}</td>"
        f"<td>KES {item.get('unit_price', '0.00')}</td></tr>"
        for item in invoice.line_items
    )
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><title>Invoice</title>
    <style>
      body {{ font-family: sans-serif; margin: 40px; }}
      h1 {{ color: #333; }} table {{ width: 100%; border-collapse: collapse; }}
      th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
      .total {{ font-weight: bold; font-size: 1.2em; }}
    </style></head>
    <body>
      <h1>{store.name}</h1>
      <p>Invoice #{invoice.id}</p>
      <p>Date: {invoice.created_at.strftime('%Y-%m-%d')}</p>
      <table>
        <tr><th>Description</th><th>Qty</th><th>Price</th></tr>
        {items_html}
      </table>
      <p class="total">Total: KES {invoice.total_amount}</p>
      <p>Pay via M-Pesa. Thank you for choosing {store.name}.</p>
    </body></html>
    """


def _build_stub_pdf(invoice) -> bytes:
    """Minimal PDF stub when WeasyPrint is not installed."""
    content = (
        f"%PDF-1.4\n"
        f"Invoice: {invoice.id}\n"
        f"Total: KES {invoice.total_amount}\n"
        f"Store: {invoice.store.name}\n"
    )
    return content.encode("utf-8")
