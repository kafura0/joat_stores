"""
Analytics views.

Story 8.3: Per-store analytics API (summary)
Story 8.2: AIEvent list (platform admin)
Story 8.4: Restaurant analytics (peak hours, table turn rate)
Story 8.5: Bar analytics (tab metrics, occupancy)
Story 8.6: Platform analytics (GMV, unit economics, TenantHealthSnapshot)
Story 8.7: First order milestone surfaced in platform store detail
"""

from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Avg, Sum
from django.utils import timezone

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.models import (
    AIEvent,
    DailyRevenueSummary,
    HourlyOrderSummary,
    StoreFirstOrderEvent,
    TenantHealthSnapshot,
)
from core.pagination import StoreCursorPagination


def _parse_date(date_str: str) -> date:
    """Parse 'yesterday', 'today', or YYYY-MM-DD."""
    if date_str == "yesterday":
        return timezone.localdate() - timedelta(days=1)
    if date_str == "today":
        return timezone.localdate()
    try:
        from datetime import datetime
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return timezone.localdate() - timedelta(days=1)


def _require_platform_admin(request):
    """Return True if request.user is a platform admin."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return False
    return getattr(user, "role", "") == "platform_admin"


# ---------------------------------------------------------------------------
# Story 8.3 — Per-store analytics summary
# ---------------------------------------------------------------------------


class StoreSummaryView(APIView):
    """
    GET /api/v1/analytics/summary/?date=yesterday

    Returns pre-aggregated daily summary for the requesting store.
    Data source: DailyRevenueSummary — never live Order queries.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        date_str = request.query_params.get("date", "yesterday")
        target_date = _parse_date(date_str)

        try:
            summary = DailyRevenueSummary.objects.get(store=request.store, date=target_date)
            return Response(
                {
                    "date": str(target_date),
                    "total_revenue": str(summary.total_revenue),
                    "order_count": summary.order_count,
                    "aov": str(summary.aov) if summary.aov else None,
                    "top_products": summary.top_products,
                    "note": "Data reflects previous day's activity. Updated daily at 00:05.",
                }
            )
        except DailyRevenueSummary.DoesNotExist:
            return Response(
                {
                    "date": str(target_date),
                    "total_revenue": "0.00",
                    "order_count": 0,
                    "aov": None,
                    "top_products": [],
                    "note": "No data for this date. Data may still be pending or no orders were placed.",
                }
            )


# ---------------------------------------------------------------------------
# Story 8.2 — AIEvent list (platform admin only)
# ---------------------------------------------------------------------------


class AIEventListView(APIView):
    """GET /api/v1/analytics/events/"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _require_platform_admin(request):
            return Response({"code": "FORBIDDEN"}, status=403)

        events = AIEvent.objects.filter(store=request.store).order_by("-occurred_at")
        paginator = StoreCursorPagination()
        page = paginator.paginate_queryset(events, request)
        from apps.analytics.serializers import AIEventSerializer
        return paginator.get_paginated_response(AIEventSerializer(page, many=True).data)


# ---------------------------------------------------------------------------
# Story 8.4 — Restaurant analytics
# ---------------------------------------------------------------------------


class RestaurantPeakHoursView(APIView):
    """GET /api/v1/analytics/restaurant/peak-hours/"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.localdate()
        week_ago = today - timedelta(days=7)

        # 24-slot array from HourlyOrderSummary, past 7 days
        summaries = HourlyOrderSummary.objects.filter(
            store=request.store,
            date__gte=week_ago,
            date__lt=today,
        ).values("hour").annotate(
            total_orders=Sum("order_count"),
            total_revenue=Sum("revenue"),
        ).order_by("hour")

        hour_map = {row["hour"]: row for row in summaries}
        slots = [
            {
                "hour": h,
                "order_count": hour_map.get(h, {}).get("total_orders", 0),
                "revenue": str(hour_map.get(h, {}).get("total_revenue") or Decimal("0")),
            }
            for h in range(24)
        ]
        return Response({"peak_hours": slots, "period_days": 7})


class RestaurantTableTurnRateView(APIView):
    """GET /api/v1/analytics/restaurant/table-turn-rate/"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.restaurant.models import TableSession

        today = timezone.now()
        week_ago = today - timedelta(days=7)

        sessions = TableSession.objects.filter(
            store=request.store,
            status=TableSession.STATUS_CLOSED,
            closed_at__gte=week_ago,
            closed_at__isnull=False,
        )

        durations = []
        for s in sessions:
            if s.opened_at and s.closed_at:
                duration_minutes = (s.closed_at - s.opened_at).total_seconds() / 60
                durations.append(duration_minutes)

        avg_minutes = (sum(durations) / len(durations)) if durations else None

        return Response(
            {
                "avg_turn_rate_minutes": round(avg_minutes, 1) if avg_minutes else None,
                "sessions_sampled": len(durations),
                "period_days": 7,
            }
        )


# ---------------------------------------------------------------------------
# Story 8.5 — Bar analytics
# ---------------------------------------------------------------------------


class BarTabMetricsView(APIView):
    """GET /api/v1/analytics/bar/tab-metrics/"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.bar.models import Tab, TabItem, TabRound

        today = timezone.now()
        week_ago = today - timedelta(days=7)

        opened = Tab.objects.filter(store=request.store, opened_at__gte=week_ago).count()
        settled = Tab.objects.filter(
            store=request.store, status=Tab.STATUS_SETTLED, settled_at__gte=week_ago
        ).count()

        completion_rate = (settled / opened) if opened > 0 else None

        # Average items per round
        rounds = TabRound.objects.filter(store=request.store, created_at__gte=week_ago)
        total_items = TabItem.objects.filter(
            store=request.store,
            round__in=rounds,
            removed_at__isnull=True,
        ).count()
        round_count = rounds.count()
        avg_round_size = (total_items / round_count) if round_count > 0 else None

        return Response(
            {
                "tab_completion_rate": round(completion_rate, 3) if completion_rate else None,
                "avg_round_size": round(avg_round_size, 1) if avg_round_size else None,
                "tabs_opened": opened,
                "tabs_settled": settled,
                "period_days": 7,
            }
        )


class BarOccupancyView(APIView):
    """GET /api/v1/analytics/bar/occupancy/"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.bar.models import Tab

        today = timezone.localdate()
        week_ago = today - timedelta(days=7)

        # Days where at least one tab was OPEN during the period
        from django.db.models import DateField
        from django.db.models.functions import TruncDate

        open_days = (
            Tab.objects.filter(store=request.store, opened_at__date__gte=week_ago)
            .annotate(day=TruncDate("opened_at"))
            .values("day")
            .distinct()
            .count()
        )

        return Response({"occupied_days": open_days, "period_days": 7})


# ---------------------------------------------------------------------------
# Story 8.6 — Platform analytics
# ---------------------------------------------------------------------------


class PlatformGMVView(APIView):
    """GET /api/v1/platform/analytics/gmv/?start=YYYY-MM-DD&end=YYYY-MM-DD"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _require_platform_admin(request):
            return Response({"code": "FORBIDDEN"}, status=403)

        start_str = request.query_params.get("start", str(timezone.localdate() - timedelta(days=30)))
        end_str = request.query_params.get("end", str(timezone.localdate()))
        start = _parse_date(start_str)
        end = _parse_date(end_str)

        agg = DailyRevenueSummary.objects.filter(date__gte=start, date__lte=end).aggregate(
            total_gmv=Sum("total_revenue"),
            total_gmv_usd=Sum("amount_usd"),
            total_orders=Sum("order_count"),
        )

        return Response(
            {
                "start": str(start),
                "end": str(end),
                "total_gmv_kes": str(agg["total_gmv"] or Decimal("0")),
                "total_gmv_usd": str(agg["total_gmv_usd"] or Decimal("0")),
                "total_orders": agg["total_orders"] or 0,
            }
        )


class PlatformUnitEconomicsView(APIView):
    """GET /api/v1/platform/analytics/unit-economics/"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _require_platform_admin(request):
            return Response({"code": "FORBIDDEN"}, status=403)

        from apps.store.models import Store, StoreStatus

        active_tenant_count = Store.objects.filter(status=StoreStatus.ACTIVE).count()
        if active_tenant_count == 0:
            return Response({"cost_per_tenant": None, "revenue_per_tenant": None, "active_tenants": 0})

        # Revenue: sum all subscription revenues for active stores
        # (stub — full implementation in Epic 9 with StoreSubscription model)
        total_sub_revenue = Decimal("0")  # TODO: Epic 9 — sum StoreSubscription.monthly_fee

        # Infrastructure cost stub (placeholder for actual cost reporting)
        infra_cost_monthly = Decimal("50000")  # KES/month (placeholder)

        return Response(
            {
                "active_tenants": active_tenant_count,
                "cost_per_tenant": str(
                    (infra_cost_monthly / active_tenant_count).quantize(Decimal("0.01"))
                ),
                "revenue_per_tenant": str(
                    (total_sub_revenue / active_tenant_count).quantize(Decimal("0.01"))
                ),
                "note": "Revenue per tenant requires Epic 9 subscription data.",
            }
        )


class TenantHealthListView(APIView):
    """GET /api/v1/platform/analytics/tenant-health/?date=yesterday"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _require_platform_admin(request):
            return Response({"code": "FORBIDDEN"}, status=403)

        date_str = request.query_params.get("date", "yesterday")
        target_date = _parse_date(date_str)

        snapshots = TenantHealthSnapshot.objects.filter(date=target_date).select_related("store")
        from apps.analytics.serializers import TenantHealthSnapshotSerializer
        return Response(TenantHealthSnapshotSerializer(snapshots, many=True).data)


# ---------------------------------------------------------------------------
# Story 8.7 — First order milestone
# ---------------------------------------------------------------------------


class StoreFirstOrderView(APIView):
    """GET /api/v1/platform/stores/{store_id}/first-order/"""

    permission_classes = [IsAuthenticated]

    def get(self, request, store_id):
        if not _require_platform_admin(request):
            return Response({"code": "FORBIDDEN"}, status=403)

        try:
            event = StoreFirstOrderEvent.objects.select_related("store", "order").get(
                store_id=store_id
            )
            return Response(
                {
                    "first_order_at": event.occurred_at.isoformat(),
                    "first_order_amount": str(event.first_order_amount) if event.first_order_amount else None,
                    "store_id": str(event.store_id),
                }
            )
        except StoreFirstOrderEvent.DoesNotExist:
            return Response({"first_order_at": None, "first_order_amount": None})


# ---------------------------------------------------------------------------
# Story 12.6 — Data export (CSV)
# ---------------------------------------------------------------------------


class DailyRevenueSummaryCSVExport(APIView):
    """
    GET /api/v1/analytics/export/csv/

    Story 12.6 — Export DailyRevenueSummary as CSV for merchant analysis.
    Query params:
    - from_date: YYYY-MM-DD (default: 30 days ago)
    - to_date:   YYYY-MM-DD (default: yesterday)

    Returns a streaming CSV response with RFC 4180 headers.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        import csv
        from django.http import StreamingHttpResponse

        today = timezone.localdate()
        try:
            from_date = date.fromisoformat(
                request.query_params.get("from_date", str(today - timedelta(days=30)))
            )
            to_date = date.fromisoformat(
                request.query_params.get("to_date", str(today - timedelta(days=1)))
            )
        except ValueError:
            return Response(
                {"errors": [{"code": "INVALID_DATE", "message": "Use YYYY-MM-DD format."}]},
                status=400,
            )

        qs = DailyRevenueSummary.objects.filter(
            store=request.store,
            date__gte=from_date,
            date__lte=to_date,
        ).order_by("date")

        def row_generator():
            yield ["date", "total_revenue_kes", "order_count", "aov_kes", "amount_usd"]
            for row in qs:
                yield [
                    str(row.date),
                    str(row.total_revenue),
                    str(row.order_count),
                    str(row.aov) if row.aov else "",
                    str(row.amount_usd),
                ]

        class EchoBuffer:
            def write(self, value):
                return value

        writer = csv.writer(EchoBuffer())

        def stream():
            for row in row_generator():
                yield writer.writerow(row)

        response = StreamingHttpResponse(stream(), content_type="text/csv")
        filename = f"revenue-{from_date}-to-{to_date}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
