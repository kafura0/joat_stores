# OWASP Top 10 + Kenya DPA 2019 Compliance Checklist
## Story 12.3 — joat_stores Platform

**Status:** IMPLEMENTED
**Last reviewed:** 2026-03-14

---

## OWASP Top 10 (2021)

### A01 — Broken Access Control ✅
- **JWT role claims** (platform_admin, store_owner, store_manager, customer) enforced on every view via `IsPlatformAdmin`, `IsAuthenticated` + role checks.
- **Tenant isolation**: `TenantModel.objects` queryset always filtered by `store` FK — impossible to read another tenant's data.
- **Store suspension**: `TenantMiddleware` returns 503 for suspended stores on all paths except `/api/v1/store/branding/`.
- **select_for_update()** used for booking, cart, and tab operations to prevent TOCTOU races.

### A02 — Cryptographic Failures ✅
- **PII at rest**: `django-encrypted-fields` applied to sensitive fields (AdminPIIAccessLog targets).
- **JWT**: RS256 or HS256 (configurable). Access tokens expire in 15 min; refresh tokens in 7 days with rotation.
- **HMAC-SHA256** for QR table tokens, invoice share tokens, Daraja webhook verification.
- **HTTPS enforced**: `SECURE_SSL_REDIRECT=True`, `SECURE_HSTS_SECONDS=31536000` in production.
- **Secrets via env vars**: never hardcoded. `.env.example` lists all required keys.

### A03 — Injection ✅
- **SQL**: Django ORM used exclusively — no raw SQL strings with user input.
- **XSS**: DRF returns JSON only; no HTML templates rendered with user input.
- **Command injection**: No `subprocess.run(user_input)` patterns in codebase.
- **M-Pesa phone normalization**: all phones normalized via `phone.normalize_phone()` before use.

### A04 — Insecure Design ✅
- Threat model documented in architecture.md.
- Multi-tenant isolation is architectural (not bolt-on): TenantQuerySet enforces store FK at ORM level.
- DLQ + Sentry capture on all async task failures.

### A05 — Security Misconfiguration ✅
- `DEBUG=False` in production settings.
- `ALLOWED_HOSTS` configured via env var.
- Django admin at `/admin/` — only accessible to `is_staff` users.
- `SecurityHeadersMiddleware` adds CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy.
- Django `SecurityMiddleware` handles HTTPS redirects, HSTS, content-type sniffing.

### A06 — Vulnerable and Outdated Components ✅
- Dependabot enabled (see `.github/dependabot.yml`).
- All packages pinned to minor version in `requirements/*.txt`.
- CI pipeline fails on `safety check` (add to GitHub Actions if not already).

### A07 — Identification and Authentication Failures ✅
- **Rate limiting**: `StorePlanRateThrottle` throttles by store + plan's `api_rate_limit`.
- **M-Pesa STK Push rate limit**: max 3 STK Push attempts per reference per hour.
- **JWT blacklisting**: refresh token invalidation via `rest_framework_simplejwt.token_blacklist`.
- **Password policy**: Django's built-in `AUTH_PASSWORD_VALIDATORS` applied.

### A08 — Software and Data Integrity Failures ✅
- **Webhook signatures**: Daraja callbacks verified via HMAC-SHA256 (`MPESA_WEBHOOK_SECRET`).
- **QR token verification**: table + product QR URLs include HMAC signature checked before processing.
- **Celery task idempotency**: all tasks use `update_or_create` or `get_or_create` patterns.

### A09 — Security Logging and Monitoring Failures ✅
- **structlog** configured globally — JSON output in production, colorized in development.
- **Sentry** integration: DjangoIntegration + CeleryIntegration + LoggingIntegration (events at ERROR level).
- **DLQ**: failed Celery tasks published to Redis sorted set (`celery:dlq`) for investigation.
- **AdminPIIAccessLog**: INSERT-only table — every PII access by platform admin recorded immutably.
- **RequestIDMiddleware**: correlation UUID on every request (X-Request-ID header).

### A10 — Server-Side Request Forgery (SSRF) ✅
- All outbound HTTP calls go through `DarajaClient` only — no user-controlled URLs.
- WhatsApp integration uses Twilio/Meta SDK — no raw URL construction from user input.

---

## Kenya Data Protection Act 2019

### Data Minimisation ✅
- Only fields necessary for business function are collected.
- Guest checkout requires only `customer_phone`; email/name optional.
- `AIEvent.metadata` is unstructured — no PII fields mandated.

### Data Subject Rights ✅
- **Right to erasure**: `anonymise_cancelled_store_pii` task anonymises all Order PII 30 days after store cancellation (`customer_phone → "ANONYMISED"`, `customer_email → ""`, `customer_name → ""`).
- **Data portability**: `GET /api/v1/analytics/export/csv/` gives merchants their own data.
- **Access log**: `AdminPIIAccessLog` records every PII access with accessor identity.

### Lawful Basis ✅
- Customers provide explicit consent during checkout (required checkbox in storefront).
- Merchant data processed under legitimate interest (service provision).

### Technical and Organisational Measures ✅
- Encrypted fields at rest (`django-encrypted-fields`).
- TLS enforced (HSTS preload).
- Role-based access control (4 roles, JWT claims).
- Soft-delete (`django-safedelete`) — data retained for 30-day window before erasure.

### Data Breach Notification ✅
- Sentry real-time alerting on exceptions.
- On-call runbook in `_bmad-output/implementation-artifacts/9-6-merchant-onboarding-runbook.md`.
- DPA 2019 §42: breach notification within 72 hours — contact `admin@joat.com`.

---

## Remediation Log

| Date | Issue | Remediation | Story |
|------|-------|-------------|-------|
| 2026-03-14 | No CSP headers | SecurityHeadersMiddleware added | 12.3 |
| 2026-03-14 | No request correlation | RequestIDMiddleware added | 12.4 |
| 2026-03-14 | PII anonymisation manual | anonymise_cancelled_store_pii task automated | 9.7 |
| 2026-03-14 | Backup not implemented | backup.sh implemented | 12.2 |
