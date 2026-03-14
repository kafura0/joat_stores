"""Payment URL configuration.

Implementation: Story 2.2, Story 2.3, Story 2.5
"""

from django.urls import path

from apps.payment.views import (
    CardPaymentScaffoldView,
    InitiateStkPushView,
    MpesaCallbackView,
    ReversePaymentView,
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
    # Story 4.7 — Card payment scaffold (501 until provider implemented)
    path("card/initiate/", CardPaymentScaffoldView.as_view(), name="card-initiate"),
]
