"""
Platform metrics view — aggregated stats for platform admin dashboard.
"""

from datetime import timedelta

from django.db.models import Count, Sum, Q
from django.utils import timezone

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.order.models import Order
from apps.saas.models import Plan, StoreSubscription, SubscriptionStatus
from apps.store.models import Store


def _is_platform_admin(user) -> bool:
    return getattr(user, "role", None) == "platform_admin"


class PlatformMetricsView(APIView):
    """
    GET /api/v1/platform/metrics/

    Returns aggregated platform-wide metrics for the admin dashboard.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_platform_admin(request.user):
            return Response({"error": "Forbidden"}, status=403)

        now = timezone.now()
        today = now.date()
        month_start = today.replace(day=1)
        last_30_days = now - timedelta(days=30)
        last_7_days = now - timedelta(days=7)
        last_90_days = now - timedelta(days=90)

        # Store metrics
        total_stores = Store.objects.count()
        active_stores = Store.objects.filter(status="active").count()
        trial_stores = Store.objects.filter(status="trial").count()
        suspended_stores = Store.objects.filter(status="suspended").count()
        dormant_stores = Store.objects.filter(
            status="active",
            updated_at__lt=last_30_days,
        ).count()

        # Stores by type
        stores_by_type = dict(
            Store.objects.values_list("tenant_type")
            .annotate(count=Count("id"))
            .values_list("tenant_type", "count")
        )

        # Stores by status
        stores_by_status = dict(
            Store.objects.values_list("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )

        # Subscription metrics
        total_subscriptions = StoreSubscription.objects.count()
        active_subscriptions = StoreSubscription.objects.filter(
            status=SubscriptionStatus.ACTIVE
        ).count()

        # Plan distribution
        plan_distribution = dict(
            StoreSubscription.objects.filter(is_active=True)
            .values_list("plan__name")
            .annotate(count=Count("id"))
            .values_list("plan__name", "count")
        )

        # Revenue (sum of renewal amounts from active subs)
        mrr = (
            StoreSubscription.objects.filter(
                status__in=[SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]
            ).aggregate(total=Sum("renewal_amount_kes"))["total"]
            or 0
        )

        # Revenue from completed orders (last 30 days)
        revenue_30d = (
            Order.objects.filter(
                status="completed",
                created_at__gte=last_30_days,
            ).aggregate(total=Sum("total"))["total"]
            or 0
        )

        # Revenue from completed orders (this month)
        revenue_mtd = (
            Order.objects.filter(
                status="completed",
                created_at__gte=month_start,
            ).aggregate(total=Sum("total"))["total"]
            or 0
        )

        # GMV (all stores, last 30 days)
        gmv_30d = (
            Order.objects.filter(
                created_at__gte=last_30_days,
            ).aggregate(total=Sum("total"))["total"]
            or 0
        )

        # Order metrics
        total_orders = Order.objects.count()
        orders_30d = Order.objects.filter(created_at__gte=last_30_days).count()
        orders_today = Order.objects.filter(created_at__date=today).count()

        # New stores this month
        new_stores_mtd = Store.objects.filter(created_at__gte=month_start).count()
        new_stores_30d = Store.objects.filter(created_at__gte=last_30_days).count()

        # Trial conversion rate
        trials_started = StoreSubscription.objects.filter(
            status__in=[SubscriptionStatus.TRIAL, SubscriptionStatus.ACTIVE]
        ).count()
        trials_converted = StoreSubscription.objects.filter(
            status=SubscriptionStatus.ACTIVE
        ).exclude(plan__name="Free").count()
        trial_conversion_rate = (
            round(trials_converted / trials_started * 100, 1)
            if trials_started > 0
            else 0
        )

        # Churn rate (stores that went inactive in last 30 days)
        churned_30d = Store.objects.filter(
            status="suspended",
            updated_at__gte=last_30_days,
        ).count()
        churn_rate = (
            round(churned_30d / total_stores * 100, 1)
            if total_stores > 0
            else 0
        )

        # Recent stores (last 5)
        recent_stores = list(
            Store.objects.order_by("-created_at")[:5].values(
                "id", "name", "slug", "tenant_type", "status", "created_at"
            )
        )
        for s in recent_stores:
            s["id"] = str(s["id"])
            s["created_at"] = s["created_at"].isoformat() if s["created_at"] else None

        # Recent subscriptions (last 5)
        recent_subs = list(
            StoreSubscription.objects.select_related("store", "plan")
            .order_by("-created_at")[:5]
            .values(
                "id",
                "status",
                "renewal_amount_kes",
                "created_at",
                "store__name",
                "plan__name",
            )
        )
        for s in recent_subs:
            s["id"] = str(s["id"])
            s["created_at"] = s["created_at"].isoformat() if s["created_at"] else None

        # Expiring soon (next 30 days)
        expiring_soon = StoreSubscription.objects.filter(
            status=SubscriptionStatus.ACTIVE,
            expires_at__lte=now + timedelta(days=30),
            expires_at__gte=now,
        ).count()

        # Failed renewals (last 30 days) — from payment transactions
        from apps.payment.models import Transaction

        failed_renewals = Transaction.objects.filter(
            reference__startswith="subscription-",
            status="failed",
            created_at__gte=last_30_days,
        ).count()

        return Response(
            {
                "stores": {
                    "total": total_stores,
                    "active": active_stores,
                    "trial": trial_stores,
                    "suspended": suspended_stores,
                    "dormant": dormant_stores,
                    "by_type": stores_by_type,
                    "by_status": stores_by_status,
                    "new_mtd": new_stores_mtd,
                    "new_30d": new_stores_30d,
                },
                "subscriptions": {
                    "total": total_subscriptions,
                    "active": active_subscriptions,
                    "plan_distribution": plan_distribution,
                    "trial_conversion_rate": trial_conversion_rate,
                    "expiring_soon": expiring_soon,
                },
                "revenue": {
                    "mrr": str(mrr),
                    "revenue_mtd": str(revenue_mtd),
                    "revenue_30d": str(revenue_30d),
                    "gmv_30d": str(gmv_30d),
                    "failed_renewals": failed_renewals,
                },
                "orders": {
                    "total": total_orders,
                    "last_30d": orders_30d,
                    "today": orders_today,
                },
                "health": {
                    "churn_rate": churn_rate,
                    "dormant_stores": dormant_stores,
                },
                "recent_stores": recent_stores,
                "recent_subscriptions": recent_subs,
            }
        )
