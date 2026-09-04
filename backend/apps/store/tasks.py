"""
Store onboarding tasks — send welcome email with PWA link and login credentials.
"""

import structlog
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from core.tasks import DLQTask

logger = structlog.get_logger(__name__)


@shared_task(
    bind=True,
    base=DLQTask,
    queue="order.notifications",
    max_retries=2,
)
def send_store_onboarding_email(
    self,
    store_id: str,
    store_name: str,
    store_slug: str,
    owner_email: str,
    temporary_password: str,
) -> None:
    """
    Send onboarding email to new store owner with:
    - Login credentials
    - PWA download link (storefront)
    - Admin dashboard link
    """
    try:
        # Build URLs
        storefront_url = f"https://{store_slug}.vercel.app"
        admin_url = settings.ADMIN_URL if hasattr(settings, "ADMIN_URL") else "https://joat-stores-admin.vercel.app"

        subject = f"Welcome to JOAT Stores — {store_name} is live!"

        # Plain text fallback
        plain_message = f"""
Welcome to JOAT Stores!

Your store "{store_name}" has been created successfully.

LOGIN CREDENTIALS
=================
Email: {owner_email}
Password: {temporary_password}

IMPORTANT: Please change your password after first login.

YOUR STORE LINKS
================
Storefront (PWA): {storefront_url}
Admin Dashboard: {admin_url}

GETTING STARTED
===============
1. Open the Admin Dashboard and log in with your credentials
2. Add your first products
3. Customize your store theme
4. Start accepting orders!

Need help? Reply to this email or visit our documentation.

— JOAT Stores Team
"""

        # Try to render HTML template, fall back to plain text
        try:
            html_message = render_to_string("emails/store_onboarding.html", {
                "store_name": store_name,
                "owner_email": owner_email,
                "temporary_password": temporary_password,
                "storefront_url": storefront_url,
                "admin_url": admin_url,
            })
        except Exception:
            html_message = None

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, "DEFAULT_FROM_EMAIL") else "noreply@joatstores.com",
            recipient_list=[owner_email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(
            "onboarding_email_sent",
            store_id=store_id,
            store_name=store_name,
            owner_email=owner_email,
        )

    except Exception as exc:
        logger.exception(
            "onboarding_email_failed",
            store_id=store_id,
            owner_email=owner_email,
        )
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(queue="analytics.reports")
def warm_branding_cache():
    """Pre-warm Redis cache for all active store branding endpoints.

    Runs every hour. Fetches branding for each active store and caches
    the response so the storefront SSR doesn't hit the DB on every page load.
    """
    import structlog
    from django.core.cache import cache
    from apps.store.models import Store, StoreSettings, StoreTheme
    from apps.store.serializers import BrandingSerializer

    log = structlog.get_logger(__name__)

    stores = Store.objects.filter(status="active")
    warmed = 0

    for store in stores:
        cache_key = f"branding:{store.id}"
        try:
            serializer = BrandingSerializer(store)
            cache.set(cache_key, serializer.data, timeout=3600)  # 1 hour
            warmed += 1
        except Exception:
            log.warning("branding_cache_warm_failed", store_id=str(store.id))

    log.info("branding_cache_warm_complete", stores=warmed)
