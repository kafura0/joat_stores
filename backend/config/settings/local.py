"""
Local development settings.
DJANGO_SETTINGS_MODULE=config.settings.local
"""

from .base import *  # noqa: F401, F403
from .base import env

# ---------------------------------------------------------------------------
# General
# ---------------------------------------------------------------------------
DEBUG = True
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="!!!SET-DJANGO-SECRET-KEY-IN-DOT-ENV!!!change-me-in-dot-env",
)
ALLOWED_HOSTS = ["localhost", "0.0.0.0", "127.0.0.1"]

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://joat_stores:password@localhost:5432/joat_stores",
    )
}

# ---------------------------------------------------------------------------
# Cache / Redis
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://127.0.0.1:6379/1")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://127.0.0.1:6379/2")

# ---------------------------------------------------------------------------
# Email (Mailpit for local testing)
# ---------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "localhost"
EMAIL_PORT = 1025
EMAIL_USE_TLS = False

# ---------------------------------------------------------------------------
# Debug toolbar
# ---------------------------------------------------------------------------
INSTALLED_APPS = INSTALLED_APPS + ["debug_toolbar"]  # noqa: F405
MIDDLEWARE = [  # noqa: F405
    "debug_toolbar.middleware.DebugToolbarMiddleware"
] + MIDDLEWARE  # noqa: F405
INTERNAL_IPS = ["127.0.0.1"]

# ---------------------------------------------------------------------------
# Sentry (disabled locally)
# ---------------------------------------------------------------------------
SENTRY_DSN = env("SENTRY_DSN", default="")

# ---------------------------------------------------------------------------
# CORS (permissive for local dev)
# ---------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = True

# Index name length check (E034) is for Oracle; Postgres allows 63 chars.
SILENCED_SYSTEM_CHECKS = [
    "models.E034",
]
