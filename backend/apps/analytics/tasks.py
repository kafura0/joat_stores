"""
Analytics async tasks.

Story 7.2: generate_daily_summary, send_merchant_weekly_digest (Beat schedule)
Story 8.1: Full DailyRevenueSummary + HourlyOrderSummary population
Story 8.2: capture_ai_event (append-only event stream)
Story 8.7: record_first_order_event (idempotent milestone)

Queue: analytics.reports
DLQ pattern: max_retries=5, countdown=60 * (2 ** retries)
"""

from decimal import Decimal

import structlog
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from core.tasks import DLQTask

logger = structlog.get_logger(__name__)

# KES → USD conversion (approximate)
KES_TO_USD = Decimal("0.0078")


@shared_task(
    bind=True,
    base=DLQTask,
    queue="analytics.reports",
    max_retries=3,
)
def populate_current_hour_summary(self) -> None:
    """
    Populate HourlyOrderSummary for the current hour across all active stores.
    Runs every hour (via Celery Beat). Ensures today's dashboard data is
    available via pre-aggregated tables rather than live Order aggregates.
    """
    try:
        from datetime import timedelta

        from django.db.models import Count, Sum

        from apps.analytics.models import HourlyOrderSummary
        from apps.order.models import Order, OrderStatus
        from apps.store.models import Store

        now = timezone.localtime()
        current_hour_start = now.replace(minute=0, second=0, microsecond=0)
        current_hour_end = current_hour_start + timedelta(hours=1)

        active_stores = Store.objects.filter(status="active")

        for store in active_stores:
            agg = Order.objects.filter(
                store=store,
                status=OrderStatus.CONFIRMED,
                confirmed_at__gte=current_hour_start,
                confirmed_at__lt=current_hour_end,
            ).aggregate(count=Count("id"), rev=Sum("total_amount"))

            HourlyOrderSummary.objects.update_or_create(
                store=store,
                date=now.date(),
                hour=now.hour,
                defaults={
                    "order_count": agg["count"] or 0,
                    "revenue": agg["rev"] or Decimal("0"),
                },
            )

        logger.info("populate_current_hour_summary_complete", hour=now.hour)
    except Exception as exc:
        logger.exception("populate_current_hour_summary_failed")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

@shared_task(
    bind=True,
    base=DLQTask,
    queue="analytics.reports",
    max_retries=5,
)
def generate_daily_summary(self, target_date_str: str = None) -> None:
    """
    Story 8.1 — Generate DailyRevenueSummary + HourlyOrderSummary + TenantHealthSnapshot
    for all active stores for the target calendar day.

    Scheduled: daily at 00:05.
    Also used for backfills: generate_daily_summary.delay("2026-03-13")
    """
    try:
        from datetime import datetime, timedelta

        if target_date_str:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        else:
            target_date = (timezone.localdate() - timedelta(days=1))

        logger.info("generate_daily_summary_start", date=str(target_date))
        _run_daily_summary(target_date)
        logger.info("generate_daily_summary_complete", date=str(target_date))

    except Exception as exc:
        logger.exception("generate_daily_summary_failed")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


def _compute_top_products(order_qs, limit: int = 5) -> list:
    """Compute top-N products by revenue from a confirmed Order queryset.

    Reads from items_snapshot JSON field. Returns list of
    {product_id, name, revenue} sorted descending by revenue.
    """
    from collections import defaultdict

    product_revenue: dict[str, dict] = defaultdict(lambda: {"name": "", "revenue": 0})
    for order in order_qs.iterator(chunk_size=200):
        for item in (order.items_snapshot or []):
            pid = str(item.get("product_id", ""))
            if not pid:
                continue
            product_revenue[pid]["name"] = item.get("name", "")
            product_revenue[pid]["revenue"] += float(item.get("price", 0)) * int(item.get("quantity", 0))

    sorted_products = sorted(
        product_revenue.items(),
        key=lambda x: x[1]["revenue"],
        reverse=True,
    )[:limit]

    return [
        {
            "product_id": pid,
            "name": data["name"],
            "revenue": str(round(data["revenue"], 2)),
        }
        for pid, data in sorted_products
    ]


def _run_daily_summary(target_date) -> None:
    """Core aggregation logic — extracted for management command reuse (backfill)."""
    from datetime import timedelta

    from django.db.models import Avg, Count, Sum

    from apps.analytics.models import DailyRevenueSummary, HourlyOrderSummary, TenantHealthSnapshot
    from apps.order.models import Order, OrderStatus
    from apps.store.models import Store

    active_stores = Store.objects.filter(status="active")

    for store in active_stores:
        day_start = timezone.make_aware(
            timezone.datetime.combine(target_date, timezone.datetime.min.time())
        )
        day_end = day_start + timedelta(days=1)

        # Aggregate confirmed orders for the day
        qs = Order.objects.filter(
            store=store,
            status=OrderStatus.CONFIRMED,
            confirmed_at__gte=day_start,
            confirmed_at__lt=day_end,
        )
        agg = qs.aggregate(
            total=Sum("total_amount"),
            count=Count("id"),
        )
        total_revenue = agg["total"] or Decimal("0")
        order_count = agg["count"] or 0
        aov = (total_revenue / order_count) if order_count > 0 else None
        amount_usd = (total_revenue * KES_TO_USD).quantize(Decimal("0.01"))

        # Upsert DailyRevenueSummary
        DailyRevenueSummary.objects.update_or_create(
            store=store,
            date=target_date,
            defaults={
                "total_revenue": total_revenue,
                "order_count": order_count,
                "aov": aov,
                "amount_usd": amount_usd,
                "top_products": _compute_top_products(qs),
            },
        )

        # Hourly breakdown
        for hour in range(24):
            hour_start = day_start + timedelta(hours=hour)
            hour_end = hour_start + timedelta(hours=1)
            hourly_agg = qs.filter(confirmed_at__gte=hour_start, confirmed_at__lt=hour_end).aggregate(
                count=Count("id"), rev=Sum("total_amount")
            )
            HourlyOrderSummary.objects.update_or_create(
                store=store,
                date=target_date,
                hour=hour,
                defaults={
                    "order_count": hourly_agg["count"] or 0,
                    "revenue": hourly_agg["rev"] or Decimal("0"),
                },
            )

        # TenantHealthSnapshot
        sub_status = ""
        is_healthy = True
        try:
            sub = store.subscription
            sub_status = sub.status
            is_healthy = sub_status not in ("past_due", "suspended", "cancelled")
        except Exception:
            pass

        TenantHealthSnapshot.objects.update_or_create(
            store=store,
            date=target_date,
            defaults={
                "gmv": total_revenue,
                "gmv_usd": amount_usd,
                "order_count": order_count,
                "subscription_status": sub_status,
                "is_healthy": is_healthy,
            },
        )


@shared_task(
    bind=True,
    base=DLQTask,
    queue="analytics.reports",
    max_retries=3,
)
def send_merchant_weekly_digest(self) -> None:
    """
    Story 7.2 — Send weekly analytics digest to store owners.
    Scheduled: Mondays at 08:00.
    Full email in Epic 12.
    """
    try:
        from datetime import timedelta

        from django.core.mail import send_mail
        from django.db.models import Sum

        from apps.analytics.models import DailyRevenueSummary
        from apps.store.models import Store

        logger.info("send_merchant_weekly_digest_start")

        cutoff = timezone.localdate() - timedelta(days=7)
        stores = Store.objects.filter(status="active")

        for store in stores:
            summary = DailyRevenueSummary.objects.filter(
                store=store, date__gte=cutoff
            ).aggregate(
                total_rev=Sum("total_revenue"),
                total_orders=Sum("order_count"),
            )
            total_rev = summary["total_rev"] or 0
            total_orders = summary["total_orders"] or 0

            if total_orders == 0:
                continue

            from django.contrib.auth import get_user_model
            User = get_user_model()
            owners = User.objects.filter(store=store, role="store_owner").only("email")[:2]
            emails = [u.email for u in owners if u.email]
            if not emails:
                continue

            send_mail(
                subject=f"Weekly Digest — {store.name}",
                message=(
                    f"Hi {store.name} owner,\n\n"
                    f"Here's your weekly summary (past 7 days):\n"
                    f"  Revenue: KES {total_rev:,.0f}\n"
                    f"  Orders: {total_orders}\n\n"
                    f"See your full dashboard for more details."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=emails,
                fail_silently=True,
            )

        logger.info("send_merchant_weekly_digest_complete")
    except Exception as exc:
        logger.exception("send_merchant_weekly_digest_failed")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(
    bind=True,
    base=DLQTask,
    queue="analytics.reports",
    max_retries=5,
)
def capture_ai_event(
    self,
    store_id: str,
    event_type: str,
    entity_id: str = "",
    customer_id: str = None,
    metadata: dict = None,
) -> None:
    """
    Story 8.2 — Append an AIEvent record.

    Called via transaction.on_commit — never inside a DB transaction.
    """
    try:
        from apps.analytics.models import AIEvent

        AIEvent.objects.create(
            store_id=store_id,
            event_type=event_type,
            entity_id=entity_id or "",
            customer_id=customer_id,
            metadata=metadata or {},
        )
    except Exception as exc:
        logger.exception("capture_ai_event_failed", event_type=event_type, store_id=store_id)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(
    bind=True,
    base=DLQTask,
    queue="analytics.reports",
    max_retries=5,
)
def record_first_order_event(self, store_id: str, order_id: str) -> None:
    """
    Story 8.7 — Record the first confirmed order milestone for a store.

    Idempotent: get_or_create ensures exactly one record per store.
    Called via transaction.on_commit after order confirmation.
    """
    try:
        from apps.analytics.models import StoreFirstOrderEvent
        from apps.order.models import Order

        # Check if first order already recorded
        if StoreFirstOrderEvent.objects.filter(store_id=store_id).exists():
            return

        # Verify this is actually the first confirmed order
        from apps.order.models import OrderStatus

        confirmed_count = Order.objects.filter(
            store_id=store_id, status=OrderStatus.CONFIRMED
        ).count()
        if confirmed_count > 1:
            return  # Not the first

        order = Order.objects.get(id=order_id)
        StoreFirstOrderEvent.objects.get_or_create(
            store_id=store_id,
            defaults={
                "order": order,
                "first_order_amount": order.total_amount,
            },
        )
        logger.info("first_order_milestone", store_id=store_id, order_id=order_id)

    except Exception as exc:
        logger.exception("record_first_order_event_failed", store_id=store_id)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
