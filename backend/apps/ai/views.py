"""
AI views — Epic 11.

Story 11.1: GET  /api/v1/ai/recommendations/        — product recommendations
Story 11.2: GET  /api/v1/ai/predictions/peak-hours/ — peak hour forecast
Story 11.3: POST /api/v1/ai/search/                 — NLP menu search

All endpoints require authentication (store_owner, store_manager, or customer).
plan.has_ai_features flag is respected: stores on plans without AI get a
clear 402 response explaining which plan unlocks AI.
"""

import structlog
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.services import (
    NLPMenuSearchService,
    PeakHourPredictionService,
    RecommendationService,
)

# ---------------------------------------------------------------------------
# Story 11.1 — AI Event capture (fires from storefront JS)
# ---------------------------------------------------------------------------


class AIEventCaptureView(APIView):
    """
    POST /api/v1/ai/events/

    Captures an AI behavioural event (product_view, cart_add, etc.).
    Dispatches to capture_ai_event Celery task so the request is non-blocking.
    Body: { event_type, entity_id?, metadata? }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.analytics.tasks import capture_ai_event
        from apps.analytics.models import AIEvent

        event_type = request.data.get("event_type")
        valid_types = [t for t, _ in AIEvent.EVENT_TYPE_CHOICES]
        if event_type not in valid_types:
            return Response(
                {"errors": [{"code": "INVALID_EVENT_TYPE", "message": f"Must be one of: {valid_types}"}]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        entity_id = request.data.get("entity_id", "")
        metadata = request.data.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}

        store = request.store
        capture_ai_event.delay(
            store_id=str(store.id),
            event_type=event_type,
            entity_id=str(entity_id),
            metadata=metadata,
        )
        return Response({"status": "accepted"}, status=status.HTTP_202_ACCEPTED)

log = structlog.get_logger(__name__)


def _check_ai_access(store) -> bool:
    """Return True if the store's subscription plan includes AI features."""
    try:
        plan = store.subscription.plan
        if plan is None:
            return False
        return plan.has_ai_features
    except Exception:
        return False  # No subscription = no AI


_AI_PLAN_ERROR = {
    "errors": [
        {
            "field": None,
            "message": "AI features require a Growth or Pro plan. Upgrade at /api/v1/saas/plans/.",
            "code": "AI_PLAN_REQUIRED",
        }
    ]
}


class AIRecommendationsView(APIView):
    """
    GET /api/v1/ai/recommendations/?phone=+254XXXXXXXXX

    Story 11.1 — Collaborative filtering product recommendations.
    Returns up to 8 recommended products for the given customer phone,
    or store-wide top products if no personal data exists.
    Requires plan.has_ai_features = True.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        store = request.store
        if not _check_ai_access(store):
            return Response(_AI_PLAN_ERROR, status=status.HTTP_402_PAYMENT_REQUIRED)

        customer_phone = request.query_params.get("phone") or getattr(request.user, "phone", None)
        service = RecommendationService()
        try:
            recommendations = service.get_recommendations(store, customer_phone=customer_phone)
        except Exception as exc:
            log.exception("recommendation_service_error", store_id=str(store.id))
            recommendations = []

        return Response({
            "recommendations": recommendations,
            "count": len(recommendations),
            "customer_phone": customer_phone,
        })


class AIPeakHourPredictionsView(APIView):
    """
    GET /api/v1/ai/predictions/peak-hours/

    Story 11.2 — Tomorrow's peak hour predictions.
    Returns 24 hourly slots with predicted_orders + confidence.
    Requires plan.has_ai_features = True.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        store = request.store
        if not _check_ai_access(store):
            return Response(_AI_PLAN_ERROR, status=status.HTTP_402_PAYMENT_REQUIRED)

        service = PeakHourPredictionService()
        try:
            predictions = service.predict(store)
        except Exception as exc:
            log.exception("peak_prediction_error", store_id=str(store.id))
            predictions = [{"hour": h, "predicted_orders": 0, "confidence": "low"} for h in range(24)]

        return Response({
            "predictions": predictions,
            "lookback_days": PeakHourPredictionService.LOOKBACK_DAYS,
        })


class AINLPSearchView(APIView):
    """
    POST /api/v1/ai/search/

    Story 11.3 — Natural language menu search.
    Body: { "q": "grilled chicken with chips" }
    Returns ranked menu items using PostgreSQL full-text search.
    Does NOT require has_ai_features — basic search is available on all plans.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        query = request.data.get("q", "").strip()
        if not query:
            return Response(
                {"errors": [{"code": "QUERY_REQUIRED", "message": "Provide a search query in 'q'."}]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        store = request.store
        service = NLPMenuSearchService()
        try:
            results = service.search(store, query)
        except Exception as exc:
            log.exception("nlp_search_error", store_id=str(store.id), query=query)
            results = []

        return Response({
            "query": query,
            "results": results,
            "count": len(results),
        })
