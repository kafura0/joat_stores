# Merchant Onboarding Runbook
## Story 9.6 — joat_stores Platform

**Audience:** Platform admins and onboarding support team
**Last updated:** 2026-03-14

---

## 1. Pre-onboarding Checklist

Before creating a store, confirm the merchant has provided:

- [ ] Business name and trading name
- [ ] M-Pesa Till / Paybill number
- [ ] Primary contact phone (Kenyan format, e.g. +254XXXXXXXXX)
- [ ] Business email address
- [ ] Tenant type: `retail` | `restaurant` | `bar` | `contracting`
- [ ] Subdomain slug (e.g. `acacia-grill` → `acacia-grill.joat.com`)
- [ ] Desired subscription plan (Free, Starter, Growth, Pro)

---

## 2. Store Provisioning (API)

### 2a. Create the store

```bash
POST /api/v1/platform/stores/
Authorization: Bearer <platform_admin_token>
Content-Type: application/json

{
  "name": "Acacia Grill",
  "slug": "acacia-grill",
  "domain": "acacia-grill.joat.com",
  "country": "KE",
  "tenant_type": "restaurant",
  "payment_methods": ["mpesa"]
}
```

**Response:** `201 Created` — includes `store.id` (UUID). Save this.

### 2b. Verify StoreSubscription was created

```bash
GET /api/v1/platform/subscriptions/?status=trial
```

Confirm the new store appears with `status: "trial"`.

### 2c. Assign a plan

```bash
PATCH /api/v1/platform/subscriptions/<subscription_id>/
{
  "plan_id": <plan_id>
}
```

---

## 3. First User Account

```bash
POST /api/v1/auth/register/
{
  "email": "owner@acacia-grill.com",
  "password": "...",
  "role": "store_owner"
}
```

Then set `X-Store-ID: <store_uuid>` header when authenticating as this user.

---

## 4. Trial Period Configuration

- Trial length is set per plan (default: 14 days).
- `StoreSubscription.trial_ends_at` is populated automatically.
- At trial end, `status` transitions to `past_due` if no payment received.
- A renewal reminder STK Push fires 3 days before expiry (Celery Beat, 09:00 daily).

---

## 5. Subscription Activation

Subscription activates automatically when the merchant completes an M-Pesa payment via:

```bash
POST /api/v1/saas/subscription/renew/
X-Store-ID: <store_uuid>
Authorization: Bearer <owner_token>

{ "phone": "+254XXXXXXXXX" }
```

Or when the platform admin manually patches status to `active`:

```bash
PATCH /api/v1/platform/subscriptions/<id>/
{ "status": "active" }
```

---

## 6. Auto-Suspension Pipeline (Story 9.7)

| Day | Event |
|-----|-------|
| Day 0 | `past_due_since` set |
| Day 3 | Renewal reminder STK Push sent (Celery Beat 09:00) |
| Day 7 | `suspend_past_due_subscriptions` task runs (01:00) → status = `suspended` |
| Day 30+ post-cancel | `anonymise_cancelled_store_pii` task runs (02:00) → Order PII erased |

Stores in `suspended` state:
- API returns `402 Payment Required` for store operations
- Storefront shows "store unavailable" page
- Data is retained (not deleted)

---

## 7. Tenant Type Activation

For `restaurant`, `bar`, `contracting` tenants:
- Tenant type is immutable once any orders exist (FR4 guard)
- Bar tenant: activate in Django admin `Store` → set `tenant_type=bar`
- Contracting tenant: no extra setup required after provisioning

---

## 8. QR Code Setup (Restaurant / Bar)

```bash
POST /api/v1/restaurant/tables/
X-Store-ID: <store_uuid>
Authorization: Bearer <owner_token>

{ "name": "Table 1", "capacity": 4 }
```

QR token is returned in `qr_token`. Print at: `https://<domain>/t/<table_id>/`

---

## 9. Smoke Tests After Onboarding

Run the following to confirm the store is live:

```bash
# 1. Public menu
GET /api/v1/store/<slug>/menu/

# 2. Storefront branding
GET /api/v1/store/<slug>/branding/

# 3. Subscription status
GET /api/v1/saas/subscription/
X-Store-ID: <store_uuid>

# Expected: { "status": "trial" | "active", "plan": { ... } }
```

---

## 10. Escalation Contacts

| Issue | Owner |
|-------|-------|
| M-Pesa STK Push failing | Platform admin → check Daraja credentials in `.env` |
| Store not resolving | TenantMiddleware → check `Store.domain` matches request Host |
| DLQ entries building up | Check `/health/workers/` → Celery worker health |
| PII erasure not running | Check Beat schedule `anonymise-cancelled-store-pii` in Flower |
