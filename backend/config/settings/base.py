"""
Base settings for joat_stores project.
All settings shared across environments live here.
Environment-specific overrides: local.py (dev), production.py (prod).
NEVER add a settings.py — always use the split: base / local / production.
"""

from pathlib import Path

import environ

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve(strict=True).parent.parent.parent.parent
APPS_DIR = ROOT_DIR / "backend"

env = environ.Env()

# ---------------------------------------------------------------------------
# Apps
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "django.contrib.postgres",  # ArrayField for Store.payment_methods
    "django.forms",
]

THIRD_PARTY_APPS = [
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "drf_spectacular",
    "django_celery_beat",
    "safedelete",
    "whitenoise.runserver_nostatic",
]

LOCAL_APPS = [
    "apps.users",
    "apps.store",
    "apps.product",
    "apps.order",
    "apps.payment",
    "apps.inventory",
    "apps.restaurant",
    "apps.bar",
    "apps.contracting",
    "apps.analytics",
    "apps.notifications",
    "apps.saas",
    "apps.ai",
    "apps.loyalty",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # Resolves request.store from domain / X-Store-ID before any view logic
    "core.middleware.TenantMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    # Story 4.9 — in-app browser detection (WhatsApp, Facebook, Instagram, Line)
    "core.middleware.InAppBrowserMiddleware",
    # Story 12.3 — OWASP security headers (CSP, X-Content-Type-Options, etc.)
    "core.middleware.SecurityHeadersMiddleware",
    # Story 12.4 — Request ID for correlation tracing (binds to structlog contextvars)
    "core.middleware.RequestIDMiddleware",
]

# ---------------------------------------------------------------------------
# URLs & WSGI
# ---------------------------------------------------------------------------
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [str(APPS_DIR / "templates")],
        "OPTIONS": {
            "loaders": [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "users.User"
LOGIN_REDIRECT_URL = "/"
LOGIN_URL = "/accounts/login/"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

_PWV = "django.contrib.auth.password_validation"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": f"{_PWV}.UserAttributeSimilarityValidator"},
    {"NAME": f"{_PWV}.MinimumLengthValidator"},
    {"NAME": f"{_PWV}.CommonPasswordValidator"},
    {"NAME": f"{_PWV}.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Allauth
# ---------------------------------------------------------------------------
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_UNIQUE_EMAIL = True
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_LOGIN_ON_GET = False

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Nairobi"
USE_I18N = True
USE_TZ = True

SITE_ID = 1

# ---------------------------------------------------------------------------
# Static & Media
# ---------------------------------------------------------------------------
STATIC_ROOT = str(ROOT_DIR / "staticfiles")
STATIC_URL = "/static/"
STATICFILES_DIRS = [str(APPS_DIR / "static")]
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_ROOT = str(APPS_DIR / "media")
MEDIA_URL = "/media/"

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [
        "core.throttling.StorePlanRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "store_plan": None,  # dynamic — read from plan.api_rate_limit
    },
    # StoreCursorPagination applied per viewset — Story 1.2
}

# ---------------------------------------------------------------------------
# SimpleJWT
# ---------------------------------------------------------------------------
from datetime import timedelta  # noqa: E402

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_OBTAIN_SERIALIZER": "apps.users.serializers.StoreTokenObtainPairSerializer",
}

# ---------------------------------------------------------------------------
# DRF Spectacular (OpenAPI)
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "joat_stores API",
    "DESCRIPTION": "Multi-tenant SaaS e-commerce for Kenyan SMEs",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 5 * 60  # 5 minutes hard limit
CELERY_TASK_SOFT_TIME_LIMIT = 60  # 60 seconds soft limit
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# Named queues
from kombu import Queue  # noqa: E402

CELERY_TASK_QUEUES = (
    Queue("order.notifications"),
    Queue("inventory.alerts"),
    Queue("billing.reminders"),
    Queue("payments.reconciliation"),
    Queue("analytics.reports"),
)
CELERY_TASK_DEFAULT_QUEUE = "order.notifications"

CELERY_TASK_ROUTES = {
    "apps.order.*": {"queue": "order.notifications"},
    "apps.inventory.*": {"queue": "inventory.alerts"},
    "apps.saas.*": {"queue": "billing.reminders"},
    "apps.payment.*": {"queue": "payments.reconciliation"},
    "apps.analytics.*": {"queue": "analytics.reports"},
}

from celery.schedules import crontab  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    # Payment tasks
    "expire-stale-stk-pushes": {
        "task": "apps.payment.tasks.expire_stale_stk_pushes",
        "schedule": timedelta(minutes=2),
    },
    "reconcile-payments-daily": {
        "task": "apps.payment.tasks.reconcile_payments",
        "schedule": crontab(hour=0, minute=30),
    },
    # Restaurant tasks
    "purge-expired-pending-orders": {
        "task": "apps.restaurant.tasks.purge_expired_pending_orders",
        "schedule": crontab(minute=0),  # every hour on the hour
    },
    # Analytics tasks (Story 7.2 / Story 8.1)
    "generate-daily-summary": {
        "task": "apps.analytics.tasks.generate_daily_summary",
        "schedule": crontab(hour=0, minute=5),  # 00:05 daily
    },
    "send-merchant-weekly-digest": {
        "task": "apps.analytics.tasks.send_merchant_weekly_digest",
        "schedule": crontab(hour=8, minute=0, day_of_week=1),  # Monday 08:00
    },
    # SaaS / billing tasks (Story 7.2 / 9.3 / 9.7)
    "send-subscription-renewal-reminder": {
        "task": "apps.saas.tasks.send_subscription_renewal_reminder",
        "schedule": crontab(hour=9, minute=0),  # daily at 09:00
    },
    "suspend-past-due-subscriptions": {
        "task": "apps.saas.tasks.suspend_past_due_subscriptions",
        "schedule": crontab(hour=1, minute=0),  # daily at 01:00
    },
    "anonymise-cancelled-store-pii": {
        "task": "apps.saas.tasks.anonymise_cancelled_store_pii",
        "schedule": crontab(hour=2, minute=0),  # daily at 02:00
    },
}

# ---------------------------------------------------------------------------
# DLQ (Dead-Letter Queue) — Story 7.1
# ---------------------------------------------------------------------------
# Redis key: "celery:dlq" (sorted set — score = failure timestamp)
# Tasks that exceed max_retries are published here for manual investigation.
# Inspect via: redis-cli ZRANGEBYSCORE celery:dlq -inf +inf WITHSCORES
# ---------------------------------------------------------------------------

# Worker health check (Story 7.3)
CELERY_WORKER_HEARTBEAT_TIMEOUT = 60  # seconds — workers older than this are "degraded"

# ---------------------------------------------------------------------------
# Multi-Tenancy (TenantMiddleware)
# ---------------------------------------------------------------------------
# Hosts that bypass store resolution entirely (platform-level subdomains)
PLATFORM_SUBDOMAINS = env.list(
    "PLATFORM_SUBDOMAINS",
    default=["admin.joat.com", "api.joat.com", "localhost", "127.0.0.1"],
)
# Request paths that bypass store resolution (health check, Django admin, schema)
MIDDLEWARE_BYPASS_PATHS = env.list(
    "MIDDLEWARE_BYPASS_PATHS",
    default=["/health/", "/admin/", "/api/v1/schema/", "/api/v1/docs/", "/api/v1/platform/", "/api/v1/auth/", "/accounts/"],
)
# Paths where suspended stores are allowed to pass through TenantMiddleware
# (so the view can return a branded error response rather than a generic 503).
SUSPENDED_PASSTHROUGH_PATHS = env.list(
    "SUSPENDED_PASSTHROUGH_PATHS",
    default=["/api/v1/store/branding/"],
)

# ---------------------------------------------------------------------------
# M-Pesa / Daraja
# ---------------------------------------------------------------------------
MPESA_ENV = env("MPESA_ENV", default="sandbox")  # "sandbox" | "production"
MPESA_CONSUMER_KEY = env("MPESA_CONSUMER_KEY", default="")
MPESA_CONSUMER_SECRET = env("MPESA_CONSUMER_SECRET", default="")
MPESA_SHORTCODE = env("MPESA_SHORTCODE", default="")
MPESA_PASSKEY = env("MPESA_PASSKEY", default="")
MPESA_CALLBACK_URL = env("MPESA_CALLBACK_URL", default="")
# Secret used to verify HMAC-SHA256 signatures on Daraja webhook callbacks
MPESA_WEBHOOK_SECRET = env("MPESA_WEBHOOK_SECRET", default="")
# Reversal API credentials (Story 2.5)
MPESA_INITIATOR_NAME = env("MPESA_INITIATOR_NAME", default="")
MPESA_SECURITY_CREDENTIAL = env("MPESA_SECURITY_CREDENTIAL", default="")

# ---------------------------------------------------------------------------
# QR Token (Story 3.3, 4.1)
# ---------------------------------------------------------------------------
HMAC_QR_SECRET = env("HMAC_QR_SECRET", default="dev-qr-secret-change-in-prod")

# ---------------------------------------------------------------------------
# Google OAuth2 PKCE (Story 4.5)
# ---------------------------------------------------------------------------
GOOGLE_OAUTH_CLIENT_ID = env("GOOGLE_OAUTH_CLIENT_ID", default="")
GOOGLE_OAUTH_CLIENT_SECRET = env("GOOGLE_OAUTH_CLIENT_SECRET", default="")

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_URLS_REGEX = r"^/api/.*$"

# ---------------------------------------------------------------------------
# Default primary key field type
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Logging (structlog + PII scrubber — Story 1.6)
# ---------------------------------------------------------------------------
import structlog  # noqa: E402
from core.audit import scrub_pii  # noqa: E402

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structlog": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.dev.ConsoleRenderer(),
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structlog",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        # PII scrubber — masks phone numbers and emails in all log output
        scrub_pii,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
