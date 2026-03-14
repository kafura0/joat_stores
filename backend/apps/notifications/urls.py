"""Notifications URL patterns — Epic 10."""

from django.urls import path

from apps.notifications.views import WhatsAppInboundWebhookView

app_name = "notifications"

urlpatterns = [
    path(
        "whatsapp/inbound/",
        WhatsAppInboundWebhookView.as_view(),
        name="whatsapp-inbound",
    ),
]
