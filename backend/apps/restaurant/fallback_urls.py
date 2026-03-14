"""
Story 3.5 — Fallback URL for wrong-table QR guard.

/t/{table_id}/ is displayed to the customer when they tap "No, wrong table"
on the QR scan confirmation screen. It returns public table info so the
customer can verify which table they're at and ask staff for help.
"""

from django.urls import path

from apps.restaurant.views import PublicTableView

urlpatterns = [
    path("", PublicTableView.as_view(), name="public-table"),
]
