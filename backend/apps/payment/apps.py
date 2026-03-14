from django.apps import AppConfig


class PaymentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.payment"
    label = "payment"

    def ready(self):
        import apps.payment.signals  # noqa: F401 — registers signal namespace
