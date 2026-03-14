"""
Loyalty Celery tasks — Epic 10.

Story 10.1: award_loyalty_points — earn points after confirmed order
Story 10.2: award_stamp — add stamp to customer's stamp card(s)
Story 10.4: update_customer_profile — upsert CustomerProfile RFM metrics
"""

import structlog
from celery import shared_task

from core.tasks import DLQTask

logger = structlog.get_logger(__name__)

# Points awarded per 100 KES spent (configurable)
POINTS_PER_100_KES = 1


@shared_task(
    bind=True,
    base=DLQTask,
    queue="order.notifications",
    max_retries=5,
)
def award_loyalty_points(self, store_id: str, customer_phone: str, amount_kes: str, order_id: str) -> None:
    """
    Story 10.1 — Award loyalty points for a confirmed order.
    Points = floor(amount_kes / 100) * POINTS_PER_100_KES.
    """
    try:
        from decimal import Decimal
        from apps.store.models import Store
        from apps.loyalty.models import LoyaltyAccount, PointsTransaction

        store = Store.objects.get(id=store_id)
        amount = Decimal(amount_kes)
        points = int(amount / 100) * POINTS_PER_100_KES
        if points <= 0:
            return

        account, _ = LoyaltyAccount.objects.get_or_create(
            store=store,
            customer_phone=customer_phone,
            defaults={"points_balance": 0, "lifetime_earned": 0},
        )
        account.earn(points, source=PointsTransaction.SOURCE_ORDER, reference=order_id)
        logger.info("loyalty_points_awarded", store_id=store_id, phone=customer_phone, points=points)

    except Exception as exc:
        logger.exception("loyalty_award_error", store_id=store_id, phone=customer_phone)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(
    bind=True,
    base=DLQTask,
    queue="order.notifications",
    max_retries=5,
)
def award_stamp(self, store_id: str, customer_phone: str, order_id: str) -> None:
    """
    Story 10.2 — Add a stamp to all active stamp cards for this store.
    If threshold is reached, enqueues a WhatsApp reward notification.
    """
    try:
        from apps.store.models import Store
        from apps.loyalty.models import CustomerStampCard, StampCard

        store = Store.objects.get(id=store_id)
        active_cards = StampCard.objects.filter(store=store, is_active=True)

        for stamp_card in active_cards:
            customer_card, _ = CustomerStampCard.objects.get_or_create(
                store=store,
                stamp_card=stamp_card,
                customer_phone=customer_phone,
                defaults={"stamps_count": 0, "redeemed_count": 0},
            )
            threshold_reached = customer_card.add_stamp(order_id)
            if threshold_reached:
                # Notify customer of reward
                send_stamp_reward_notification.delay(
                    store_id=store_id,
                    customer_phone=customer_phone,
                    reward_description=stamp_card.reward_description,
                )
                logger.info(
                    "stamp_threshold_reached",
                    store_id=store_id,
                    phone=customer_phone,
                    card=stamp_card.name,
                )

    except Exception as exc:
        logger.exception("award_stamp_error", store_id=store_id, phone=customer_phone)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(
    bind=True,
    base=DLQTask,
    queue="order.notifications",
    max_retries=5,
)
def update_customer_profile(
    self,
    store_id: str,
    customer_phone: str,
    amount_kes: str,
    customer_name: str = "",
    customer_email: str = "",
) -> None:
    """
    Story 10.4 — Upsert CustomerProfile RFM metrics after a confirmed order.
    """
    try:
        from decimal import Decimal
        from django.utils import timezone
        from apps.store.models import Store
        from apps.loyalty.models import CustomerProfile

        store = Store.objects.get(id=store_id)
        amount = Decimal(amount_kes)

        profile, created = CustomerProfile.objects.get_or_create(
            store=store,
            customer_phone=customer_phone,
            defaults={
                "customer_name": customer_name,
                "customer_email": customer_email,
            },
        )
        profile.record_order(amount)
        logger.info("customer_profile_updated", store_id=store_id, phone=customer_phone)

    except Exception as exc:
        logger.exception("update_customer_profile_error", store_id=store_id, phone=customer_phone)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(
    bind=True,
    base=DLQTask,
    queue="order.notifications",
    max_retries=3,
)
def send_stamp_reward_notification(
    self,
    store_id: str,
    customer_phone: str,
    reward_description: str,
) -> None:
    """
    Story 10.2 / 10.3 — Send a WhatsApp message when a stamp card threshold is reached.
    """
    try:
        from apps.notifications.tasks import send_whatsapp_notification
        message = (
            f"🎉 Congratulations! You've completed your stamp card.\n"
            f"Your reward: {reward_description}\n"
            f"Show this message at the counter to redeem."
        )
        send_whatsapp_notification.delay(
            store_id=store_id,
            recipient_phone=customer_phone,
            message_body=message,
            template="stamp_threshold",
        )
    except Exception as exc:
        logger.exception("stamp_reward_notification_error", store_id=store_id, phone=customer_phone)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
