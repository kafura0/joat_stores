"""
AI URL patterns — Story 9.5 scaffold (501 endpoints).
Full implementation: Epic 11.
"""

from django.urls import path

from apps.ai.views import (
    AIRecommendationsView,
    AINLPSearchView,
    AIPeakHourPredictionsView,
)

app_name = "ai"

urlpatterns = [
    path("recommendations/", AIRecommendationsView.as_view(), name="recommendations"),
    path("predictions/peak-hours/", AIPeakHourPredictionsView.as_view(), name="peak-hour-predictions"),
    path("search/", AINLPSearchView.as_view(), name="nlp-search"),
]
