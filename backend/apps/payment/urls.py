"""Payment URL configuration.

Implementation: Story 2.2, Story 2.3, Story 2.5
"""

from django.urls import path

from apps.payment.views import (
    C2BCallbackView,
    C2BRegisterView,
    C2BValidationView,
    CardPaymentInitiateView,
    InitiateStkPushView,
    MpesaCallbackView,
    ReversePaymentView,
    StripeWebhookView,
)

app_name = "payment"

urlpatterns = [
    path("initiate-stk/", InitiateStkPushView.as_view(), name="initiate-stk"),
    path("mpesa-callback/", MpesaCallbackView.as_view(), name="mpesa-callback"),
    path(
        "<uuid:transaction_id>/reverse/",
        ReversePaymentView.as_view(),
        name="reverse-payment",
    ),
    # Story 2.6 — Card payments via Stripe
    path("card/initiate/", CardPaymentInitiateView.as_view(), name="card-initiate"),
    path("stripe-webhook/", StripeWebhookView.as_view(), name="stripe-webhook"),
    # C2B — till number / paybill customer-initiated payments
    path("c2b-callback/", C2BCallbackView.as_view(), name="c2b-callback"),
    path("c2b-validation/", C2BValidationView.as_view(), name="c2b-validation"),
    path("c2b-register/", C2BRegisterView.as_view(), name="c2b-register"),
]
