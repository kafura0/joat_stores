#!/usr/bin/env python3
"""
Helper script to generate secure random secrets for the production environment variables.
Run this script to obtain values for:
- DJANGO_SECRET_KEY
- HMAC_QR_SECRET
- MPESA_WEBHOOK_SECRET
- WHATSAPP_WEBHOOK_VERIFY_TOKEN
"""

import secrets
import string

def generate_django_secret():
    # Django secret key generation logic (similar to django.core.management.utils.get_random_secret_key)
    chars = string.ascii_letters + string.digits + string.punctuation
    # Remove chars that might cause issue in some terminal wrappers or configs (like quotes, backslashes)
    chars = chars.replace("'", "").replace('"', "").replace("\\", "")
    return "".join(secrets.choice(chars) for _ in range(50))

def main():
    print("=" * 60)
    print("PRODUCTION SECRETS GENERATOR FOR JOAT STORES")
    print("=" * 60)
    print("Use these values when configuring environment variables on Render:")
    print()
    print(f"DJANGO_SECRET_KEY:\n{generate_django_secret()}\n")
    print(f"HMAC_QR_SECRET (Hex):\n{secrets.token_hex(32)}\n")
    print(f"MPESA_WEBHOOK_SECRET (Hex):\n{secrets.token_hex(24)}\n")
    print(f"WHATSAPP_WEBHOOK_VERIFY_TOKEN:\n{secrets.token_urlsafe(16)}\n")
    print("=" * 60)

if __name__ == "__main__":
    main()
