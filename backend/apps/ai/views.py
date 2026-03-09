from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class AIRecommendationsView(APIView):
    """Placeholder. Returns 501 until Phase 3 AI engine is implemented."""

    def get(self, request):
        return Response(
            {
                "errors": [
                    {
                        "field": None,
                        "message": "AI recommendations not yet available.",
                        "code": "NOT_IMPLEMENTED",
                    }
                ]
            },
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )
