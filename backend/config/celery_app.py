"""
Celery configuration for joat_stores.
5 named queues: order.notifications, inventory.alerts, billing.reminders,
payments.reconciliation, analytics.reports.
DLQ config: Story 1.1b.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("joat_stores")

# Use CELERY_ prefix for all celery settings in Django settings
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks from all INSTALLED_APPS
app.autodiscover_tasks()

# Named queues — used in CELERY_TASK_ROUTES (base.py)
app.conf.task_queues_max_priority = 10
