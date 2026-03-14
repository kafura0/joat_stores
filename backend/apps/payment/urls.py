"""Payment URL configuration.

Implementation: Story 2.2, Story 2.3, Story 2.5
"""

from django.urls import path

from apps.payment.views import (
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
]
