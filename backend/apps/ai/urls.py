"""
AI URL patterns — Story 9.5 scaffold (now fully implemented in Epic 11).
"""

from django.urls import path

from apps.ai.views import (
    AIEventCaptureView,
    AIRecommendationsView,
    AINLPSearchView,
    AIPeakHourPredictionsView,
)

app_name = "ai"

urlpatterns = [
    # Story 11.1 — Recommendations + event capture
    path("recommendations/", AIRecommendationsView.as_view(), name="recommendations"),
    path("events/", AIEventCaptureView.as_view(), name="event-capture"),
    # Story 11.2 — Peak hour predictions
    path("predictions/peak-hours/", AIPeakHourPredictionsView.as_view(), name="peak-hour-predictions"),
    # Story 11.3 — NLP menu search
    path("search/", AINLPSearchView.as_view(), name="nlp-search"),
]
