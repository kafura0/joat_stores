"""
Contracting URL configuration.

Implementation: Stories 6.1-6.6
"""

from django.urls import path

from apps.contracting.views import (
    BookingConfirmView,
    BookingListView,
    CreateInvoiceView,
    CreateQuoteView,
    InvoiceDownloadView,
    InvoicePayView,
    JobDetailView,
    JobTransitionView,
    MilestoneUpdateView,
    QuoteAcceptView,
    QuoteRejectView,
    QuoteRequestListView,
    ServiceAvailabilityView,
    ServiceDetailView,
    ServiceListView,
)

app_name = "contracting"

urlpatterns = [
    # Story 6.1 — Service catalog
    path("services/", ServiceListView.as_view(), name="service-list"),
    path("services/<uuid:service_id>/", ServiceDetailView.as_view(), name="service-detail"),
    path(
        "services/<uuid:service_id>/availability/",
        ServiceAvailabilityView.as_view(),
        name="service-availability",
    ),
    # Story 6.2 — Bookings
    path("bookings/", BookingListView.as_view(), name="booking-list"),
    path(
        "bookings/<uuid:booking_id>/confirm/",
        BookingConfirmView.as_view(),
        name="booking-confirm",
    ),
    # Story 6.3 — Quotes
    path("quote-requests/", QuoteRequestListView.as_view(), name="quote-request-list"),
    path(
        "quote-requests/<uuid:quote_request_id>/quote/",
        CreateQuoteView.as_view(),
        name="create-quote",
    ),
    path("quotes/<uuid:quote_id>/accept/", QuoteAcceptView.as_view(), name="quote-accept"),
    path("quotes/<uuid:quote_id>/reject/", QuoteRejectView.as_view(), name="quote-reject"),
    # Story 6.4 — Jobs + Milestones
    path("jobs/<uuid:job_id>/", JobDetailView.as_view(), name="job-detail"),
    path("jobs/<uuid:job_id>/transition/", JobTransitionView.as_view(), name="job-transition"),
    path("milestones/<uuid:milestone_id>/", MilestoneUpdateView.as_view(), name="milestone-update"),
    # Story 6.5 — Invoice + PDF
    path("jobs/<uuid:job_id>/invoice/", CreateInvoiceView.as_view(), name="create-invoice"),
    path(
        "invoices/<str:token>/download/",
        InvoiceDownloadView.as_view(),
        name="invoice-download",
    ),
    # Story 6.6 — Invoice payment
    path("invoices/<uuid:invoice_id>/pay/", InvoicePayView.as_view(), name="invoice-pay"),
]
