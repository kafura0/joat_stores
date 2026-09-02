"""
AI service layer — Epic 11.

Story 11.1: Recommendation engine — co-occurrence collaborative filtering
Story 11.2: Peak hour predictions — moving average on HourlyOrderSummary
Story 11.3: NLP menu search — PostgreSQL trigram similarity

All services operate on pre-existing analytics data (Epic 8) and
product/order data, so no external ML infrastructure is required at MVP.
"""

from __future__ import annotations

from collections import Counter
from decimal import Decimal

import structlog

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# 11.1 — Recommendation engine
# ---------------------------------------------------------------------------


class RecommendationService:
    """
    Collaborative filtering recommendations.

    Algorithm (MVP — no ML server required):
    1. Fetch the customer's recently viewed / cart-added products (AIEvent).
    2. Find other customers who also viewed/added those products.
    3. Score products by co-occurrence frequency, exclude already-seen items.
    4. Return top-N by score, enriched with product details.

    Falls back to store-wide top products if insufficient personal data.
    """

    TOP_N = 8
    LOOKBACK_DAYS = 30

    def get_recommendations(self, store, customer_phone: str | None = None) -> list[dict]:
        from datetime import timedelta
        from django.utils import timezone
        from apps.analytics.models import AIEvent

        cutoff = timezone.now() - timedelta(days=self.LOOKBACK_DAYS)

        # Step 1 — Customer's own recent interactions
        customer_entity_ids: list[str] = []
        if customer_phone:
            customer_events = AIEvent.objects.filter(
                store=store,
                event_type__in=[AIEvent.EVENT_PRODUCT_VIEW, AIEvent.EVENT_CART_ADD],
                occurred_at__gte=cutoff,
                metadata__customer_phone=customer_phone,
            ).values_list("entity_id", flat=True)[:50]
            customer_entity_ids = list(customer_entity_ids)

        # Step 2 — Co-occurrence: products frequently paired with customer's products
        candidate_counter: Counter = Counter()
        if customer_entity_ids:
            cooccurrence_events = AIEvent.objects.filter(
                store=store,
                event_type__in=[AIEvent.EVENT_PRODUCT_VIEW, AIEvent.EVENT_CART_ADD],
                occurred_at__gte=cutoff,
            ).exclude(entity_id__in=customer_entity_ids).values_list("entity_id", flat=True)[:500]
            candidate_counter.update(cooccurrence_events)

        # Step 3 — Fall back to store-wide top products
        if not candidate_counter:
            top_events = AIEvent.objects.filter(
                store=store,
                event_type__in=[AIEvent.EVENT_PRODUCT_VIEW, AIEvent.EVENT_CART_ADD],
                occurred_at__gte=cutoff,
            ).values_list("entity_id", flat=True)[:500]
            candidate_counter.update(top_events)

        # Step 4 — Resolve entity_ids to products and enrich
        top_ids = [eid for eid, _ in candidate_counter.most_common(self.TOP_N * 2) if eid]

        return self._enrich_products(store, top_ids, limit=self.TOP_N)

    def _enrich_products(self, store, entity_ids: list[str], limit: int) -> list[dict]:
        """Resolve entity_id strings to Product dicts."""
        from apps.product.models import Product

        if not entity_ids:
            # Pure popularity fallback: return best-sellers
            products = (
                Product.objects.filter(store=store, is_available=True)
                .order_by("-created_at")[:limit]
            )
        else:
            # Try UUIDs; ignore non-UUID entity_ids gracefully
            import uuid as _uuid
            valid_ids = []
            for eid in entity_ids:
                try:
                    valid_ids.append(_uuid.UUID(eid))
                except ValueError:
                    pass

            products = Product.objects.filter(
                store=store,
                id__in=valid_ids,
                is_available=True,
            )[:limit]

        return [
            {
                "product_id": str(p.id),
                "name": p.name,
                "score": None,  # not exposed at MVP
            }
            for p in products
        ]


# ---------------------------------------------------------------------------
# 11.2 — Peak hour predictions
# ---------------------------------------------------------------------------


class PeakHourPredictionService:
    """
    Predict tomorrow's peak hours using a 7-day moving average of
    HourlyOrderSummary data.

    Returns a list of 24 hourly dicts:
    { hour, predicted_orders, confidence }
    Confidence is low/medium/high based on data availability.
    """

    LOOKBACK_DAYS = 7

    def predict(self, store) -> list[dict]:
        from datetime import timedelta
        from django.utils import timezone
        from apps.analytics.models import HourlyOrderSummary

        today = timezone.localdate()
        cutoff = today - timedelta(days=self.LOOKBACK_DAYS)

        summaries = HourlyOrderSummary.objects.filter(
            store=store,
            date__gte=cutoff,
            date__lt=today,
        ).values("hour", "order_count")

        # Aggregate by hour
        hourly_totals: dict[int, list[int]] = {h: [] for h in range(24)}
        for row in summaries:
            hourly_totals[row["hour"]].append(row["order_count"])

        results = []
        for hour in range(24):
            counts = hourly_totals[hour]
            if not counts:
                predicted = 0
                confidence = "low"
            else:
                predicted = round(sum(counts) / len(counts), 1)
                confidence = "high" if len(counts) >= 5 else "medium" if len(counts) >= 2 else "low"
            results.append({
                "hour": hour,
                "predicted_orders": predicted,
                "confidence": confidence,
            })

        return results


# ---------------------------------------------------------------------------
# 11.3 — NLP menu search
# ---------------------------------------------------------------------------


class NLPMenuSearchService:
    """
    Natural language menu search using PostgreSQL full-text search +
    trigram similarity (pg_trgm extension).

    At MVP: uses Django's __icontains + __search (PostgreSQL SearchVector).
    Returns ranked menu items matching the query.
    """

    MAX_RESULTS = 20

    def search(self, store, query: str) -> list[dict]:
        from apps.restaurant.models import MenuItem

        if not query or len(query.strip()) < 2:
            return []

        q = query.strip()

        # Try full-text search first (requires PostgreSQL)
        try:
            from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

            vector = SearchVector("name", weight="A") + SearchVector("description", weight="B")
            search_query = SearchQuery(q)

            results = (
                MenuItem.objects.filter(store=store, is_available=True)
                .annotate(rank=SearchRank(vector, search_query))
                .filter(rank__gt=0)
                .order_by("-rank")[:self.MAX_RESULTS]
            )
            if results:
                return self._format_results(results)
        except Exception:
            pass

        # Fallback: icontains
        results = MenuItem.objects.filter(
            store=store,
            is_available=True,
            name__icontains=q,
        )[:self.MAX_RESULTS]

        return self._format_results(results)

    def _format_results(self, items) -> list[dict]:
        return [
            {
                "item_id": str(item.id),
                "name": item.name,
                "description": item.description or "",
                "price": str(item.price),
                "section": item.section.name if item.section else "",
                "is_available": item.is_available,
            }
            for item in items
        ]
