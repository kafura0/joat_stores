"""Payment Django signals.

Integration point for other apps to react to payment events.
Receivers connect via apps.payment.signals in their own apps.py ready().

Example receiver (in apps/order/apps.py):
    from apps.payment.signals import payment_confirmed
    payment_confirmed.connect(handle_payment_confirmed, sender=None)
"""

import django.dispatch

# Fired when a MpesaTransaction transitions to CONFIRMED status.
# kwargs: transaction=<MpesaTransaction instance>
payment_confirmed = django.dispatch.Signal()
