"""
Phone normalization re-export for the payment app.

The canonical implementation lives in core/phone.py to preserve the
core/ → apps/ dependency direction. This module re-exports everything
so payment-layer code can import from apps.payment.phone directly.

Implementation: Story 2.0
"""

from core.phone import PhoneNormalizationError, normalize_phone

__all__ = ["PhoneNormalizationError", "normalize_phone"]
