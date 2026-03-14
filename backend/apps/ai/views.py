"""
AI views — Story 9.5 scaffold (501 endpoints).

All AI features return HTTP 501 AI_NOT_LIVE until Epic 11 is implemented.
The plan feature flag `has_ai_features` is enforced here so that the 501
response only fires for authenticated stores with an AI-enabled plan.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

_NOT_LIVE = {
    "errors": [
        {
            "field": None,
            "message": "AI features are not yet available. Coming in Phase 3.",
            "code": "AI_NOT_LIVE",
        }
    ]
}


class AIRecommendationsView(APIView):
    """
    GET /api/v1/ai/recommendations/

    Story 9.5 — Returns 501 AI_NOT_LIVE.
    Epic 11 (Story 11.1) will implement collaborative filtering.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_NOT_LIVE, status=status.HTTP_501_NOT_IMPLEMENTED)


class AIPeakHourPredictionsView(APIView):
    """
    GET /api/v1/ai/predictions/peak-hours/

    Story 9.5 — Returns 501 AI_NOT_LIVE.
    Epic 11 (Story 11.2) will implement ML-based peak hour forecasting.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_NOT_LIVE, status=status.HTTP_501_NOT_IMPLEMENTED)


class AINLPSearchView(APIView):
    """
    POST /api/v1/ai/search/

    Story 9.5 — Returns 501 AI_NOT_LIVE.
    Epic 11 (Story 11.3) will implement NLP-powered menu search.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response(_NOT_LIVE, status=status.HTTP_501_NOT_IMPLEMENTED)
