# JOAT Stores — Architecture Diagrams

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INTERNET                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           NGINX (:80)                                        │
│                    Reverse Proxy + SSL Termination                           │
│              Per-tenant domain routing (tenant configs)                      │
└─────────────────────────────────────────────────────────────────────────────┘
                    │                           │
        ┌───────────┴───────────┐   ┌───────────┴───────────┐
        ▼                       ▼   ▼                       ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│  STOREFRONT   │       │   DJANGO API  │       │     ADMIN     │
│  Next.js :3000│       │    :8000      │       │  Next.js :3001│
│               │       │               │       │               │
│  Customer-    │       │  REST API     │       │  Merchant     │
│  facing       │       │  + Celery     │       │  Dashboard    │
└───────────────┘       └───────┬───────┘       └───────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            ▼                   ▼                   ▼
    ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
    │  PostgreSQL   │   │     Redis     │   │  Celery       │
    │  :5432        │   │     :6379     │   │  Worker       │
    │               │   │               │   │  Beat         │
    │  Primary DB   │   │  Cache +      │   │  Flower :5555 │
    │               │   │  Broker       │   │               │
    └───────────────┘   └───────────────┘   └───────────────┘
```

---

## Tenant Resolution Flow

```
Request arrives
        │
        ▼
┌─────────────────────────────────────────┐
│           TenantMiddleware               │
│                                          │
│  1. Check Host header                    │
│     ├── Matches tenant domain?           │
│     │   └── Yes → request.store = Store  │
│     │                                    │
│  2. Check X-Store-ID header              │
│     ├── Valid UUID?                      │
│     │   └── Yes → request.store = Store  │
│     │                                    │
│  3. No match found                       │
│     └── Return 404                       │
└─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│        Is request.store set?             │
│                                          │
│  ├── Yes → Continue to view              │
│  │          (TenantQuerySet filters      │
│  │           by store_id)                │
│  │                                       │
│  └── No → Platform-level request         │
│           (admin.joat.com, api.joat.com) │
└─────────────────────────────────────────┘
```

---

## JWT Authentication Flow

```
User submits credentials
        │
        ▼
┌─────────────────────────────────────────┐
│     POST /api/v1/auth/token/             │
│                                          │
│  1. Validate email + password            │
│  2. Check store membership               │
│  3. Generate access token (in body)      │
│     └── Claims: {                        │
│           "user_id": 123,                │
│           "store_id": "uuid",            │
│           "role": "store_owner",         │
│           "exp": now + 15min             │
│         }                                │
│  4. Generate refresh token (httpOnly)    │
│     └── Set-Cookie: refresh_token=...    │
└─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│     Subsequent requests                  │
│                                          │
│  Header: Authorization: Bearer <access>  │
│                                          │
│  1. DRF validates JWT signature          │
│  2. Extracts user_id, store_id, role     │
│  3. Sets request.user                    │
│  4. TenantMiddleware sets request.store  │
│  5. RBAC checks JWT role claim           │
└─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│     Token refresh                        │
│                                          │
│  POST /api/v1/auth/token/refresh/        │
│  Cookie: refresh_token=...               │
│                                          │
│  1. Validate refresh token               │
│  2. Check token family (reuse detection) │
│  3. Rotate both tokens                   │
│  4. Return new access + new refresh      │
└─────────────────────────────────────────┘
```

---

## Order Lifecycle State Machine

```
                    ┌─────────────┐
                    │   PENDING   │
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           ▼                               ▼
    ┌─────────────┐                 ┌─────────────┐
    │  CANCELLED  │                 │  CONFIRMED  │
    └─────────────┘                 └──────┬──────┘
                                           │
                               ┌───────────┼───────────┐
                               ▼                       ▼
                        ┌─────────────┐         ┌─────────────┐
                        │  CANCELLED  │         │  FULFILLED  │
                        │  (w/reversal│         └──────┬──────┘
                        └─────────────┘                │
                                                       ▼
                                                ┌─────────────┐
                                                │  COMPLETED  │
                                                │  (auto 48h) │
                                                └─────────────┘

Valid Transitions:
  PENDING → CONFIRMED (payment confirmed)
  PENDING → CANCELLED (customer cancels)
  CONFIRMED → FULFILLED (items dispatched)
  CONFIRMED → CANCELLED (merchant cancel + reversal)
  FULFILLED → COMPLETED (auto after 48h)
  COMPLETED / CANCELLED → terminal
```

---

## M-Pesa Payment Flow

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│   Customer    │     │  DJANGO API   │     │    DARAJA     │
│   Checkout    │     │               │     │  (Safaricom)  │
└───────┬───────┘     └───────┬───────┘     └───────┬───────┘
        │                     │                     │
        │  POST /checkout     │                     │
        │────────────────────>│                     │
        │                     │                     │
        │                     │  STK Push Request   │
        │                     │────────────────────>│
        │                     │                     │
        │                     │  CheckoutRequestID  │
        │                     │<────────────────────│
        │                     │                     │
        │   "Check your phone"│                     │
        │<────────────────────│                     │
        │                     │                     │
        │  User enters PIN    │                     │
        │──────────────────────────────────────────>│
        │                     │                     │
        │                     │  Webhook callback   │
        │                     │<────────────────────│
        │                     │  (HMAC verified)    │
        │                     │                     │
        │                     │  Process callback   │
        │                     │  Update payment     │
        │                     │  Update order       │
        │                     │                     │
        │  Order confirmed    │                     │
        │<────────────────────│                     │
```

---

## Restaurant QR Dine-In Flow

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│   Customer    │     │  DJANGO API   │     │    Kitchen    │
│   (at table)  │     │               │     │   Display     │
└───────┬───────┘     └───────┬───────┘     └───────┬───────┘
        │                     │                     │
        │  Scan QR code       │                     │
        │  (store_id +        │                     │
        │   table_id + HMAC)  │                     │
        │────────────────────>│                     │
        │                     │                     │
        │  Validate token     │                     │
        │  Confirm table      │                     │
        │<────────────────────│                     │
        │                     │                     │
        │  Browse menu        │                     │
        │  Add items          │                     │
        │  Place order        │                     │
        │────────────────────>│                     │
        │                     │                     │
        │                     │  Create DineInOrder │
        │                     │  Create KitchenTicket│
        │                     │                     │
        │                     │  PENDING ticket     │
        │                     │────────────────────>│
        │                     │                     │
        │                     │                     │  Staff picks up
        │                     │                     │  IN_PROGRESS
        │                     │<────────────────────│
        │                     │                     │
        │                     │                     │  Order ready
        │                     │  COMPLETED          │
        │                     │<────────────────────│
        │                     │                     │
        │  Order ready!       │                     │
        │<────────────────────│                     │
        │                     │                     │
        │  Request bill       │                     │
        │────────────────────>│                     │
        │                     │                     │
        │  Pay via M-Pesa     │                     │
        │────────────────────>│                     │
        │                     │  STK Push           │
        │                     │────────────────────>│
```

---

## Bar Tab Flow

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│   Customer    │     │  Staff        │     │    Kitchen    │
│               │     │               │     │               │
└───────┬───────┘     └───────┬───────┘     └───────┬───────┘
        │                     │                     │
        │  "Open a tab"       │                     │
        │────────────────────>│                     │
        │                     │  Create Tab (OPEN)  │
        │                     │                     │
        │  Tab opened         │                     │
        │<────────────────────│                     │
        │                     │                     │
        │  Order round 1      │                     │
        │────────────────────>│                     │
        │                     │  Add Round + Items  │
        │                     │  (age check if 18+) │
        │                     │  (happy hour price) │
        │                     │────────────────────>│
        │                     │                     │
        │  Order round 2      │                     │
        │────────────────────>│                     │
        │                     │  Add Round + Items  │
        │                     │────────────────────>│
        │                     │                     │
        │  "Close tab"        │                     │
        │────────────────────>│                     │
        │                     │  OPEN → BILL_REQUESTED│
        │                     │                     │
        │  View bill          │                     │
        │<────────────────────│                     │
        │                     │                     │
        │  Pay (single/split) │                     │
        │────────────────────>│                     │
        │                     │  STK Push(s)        │
        │                     │  BILL_REQUESTED → SETTLED│
```

---

## Celery Task Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CELERY WORKER                             │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  │ order.           │  │ inventory.       │  │ billing.         │
│  │ notifications    │  │ alerts           │  │ reminders        │
│  │                  │  │                  │  │                  │
│  │ • order_confirm  │  │ • check_low_stock│  │ • billing_remind │
│  │ • whatsapp       │  │ • low_stock_alert│  │ • subscription_  │
│  │ • loyalty_points │  │                  │  │   renewal        │
│  │ • stamp_award    │  │                  │  │ • suspend_past   │
│  │ • customer_      │  │                  │  │ • anonymise_pii  │
│  │   profile        │  │                  │  │                  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐                      │
│  │ payments.        │  │ analytics.       │                      │
│  │ reconciliation   │  │ reports          │                      │
│  │                  │  │                  │                      │
│  │ • process_       │  │ • daily_summary  │                      │
│  │   mpesa_callback │  │ • hourly_summary │                      │
│  │ • reconcile_     │  │ • weekly_digest  │                      │
│  │   payments       │  │ • capture_ai     │                      │
│  │ • expire_stale   │  │ • first_order    │                      │
│  │ • initiate_      │  │                  │                      │
│  │   reversal       │  │                  │                      │
│  └──────────────────┘  └──────────────────┘                      │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │                      DLQ (Dead Letter Queue)                  ││
│  │  Redis sorted set: celery:dlq                                 ││
│  │  Stores failed tasks after 5 retries                          ││
│  │  Exponential backoff: 60s, 120s, 240s, 480s, 960s            ││
│  └──────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                     CELERY BEAT SCHEDULE                         │
│                                                                  │
│  Every 2 min:   expire_stale_stk_pushes                         │
│  Every hour:    purge_expired_pending_orders                     │
│  Every hour:    populate_current_hour_summary                    │
│  Daily 00:05:   generate_daily_summary                          │
│  Daily 00:30:   reconcile_payments                              │
│  Daily 01:00:   suspend_past_due_subscriptions                  │
│  Daily 02:00:   anonymise_cancelled_store_pii                   │
│  Daily 09:00:   send_subscription_renewal_reminder               │
│  Monday 08:00:  send_merchant_weekly_digest                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Multi-Tenant Data Model

```
┌─────────────────────────────────────────────────────────────────┐
│                     TENANT ROOT: Store                           │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  id (UUID) │ name │ slug │ domain │ tenant_type │ status  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────┐    ┌──────────────────────┐           │
│  │ StoreSettings        │    │ StoreTheme           │           │
│  │ tagline, logo,       │    │ 45 design tokens     │           │
│  │ low_stock_threshold  │    │ colours, fonts, etc  │           │
│  └──────────────────────┘    └──────────────────────┘           │
│                                                                  │
│  All domain models inherit TenantModel:                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  id (UUID) │ store (FK) │ ...fields... │ soft_delete       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Models:                                                         │
│  ├── Product → Variant → ProductImage                           │
│  ├── Category                                                    │
│  ├── Order (items_snapshot JSON)                                 │
│  ├── MpesaTransaction                                            │
│  ├── MenuSection → MenuItem → ModifierGroup → Modifier          │
│  ├── Table → TableSession → DineInOrder → KitchenTicket         │
│  ├── Tab → TabRound → TabItem                                    │
│  ├── Service → AvailabilitySlot → ServiceBooking                │
│  ├── QuoteRequest → Quote → Job → JobMilestone → Invoice       │
│  ├── LoyaltyAccount → PointsTransaction                         │
│  ├── StampCard → CustomerStampCard → CustomerStamp              │
│  └── WhatsAppMessage, WhatsAppInboundMessage                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        VERCEL (Frontends)                        │
│                                                                  │
│  ┌──────────────────────┐    ┌──────────────────────┐           │
│  │ joat-storefront      │    │ joat-admin           │           │
│  │ (storefront.vercel.  │    │ (admin.vercel.app)   │           │
│  │  app)                │    │                      │           │
│  └──────────────────────┘    └──────────────────────┘           │
│                                                                  │
│  Environment: NEXT_PUBLIC_API_URL → Render API                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         RENDER (Backend)                         │
│                                                                  │
│  ┌──────────────────────┐    ┌──────────────────────┐           │
│  │ joat-stores-api      │    │ joat-stores-celery   │           │
│  │ (Django Web Service) │    │ (Celery Worker)      │           │
│  └──────────────────────┘    └──────────────────────┘           │
│                                                                  │
│  Environment: DATABASE_URL → Supabase                            │
│               REDIS_URL → Upstash                                │
│               MPESA_* → Daraja credentials                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
┌──────────────────────┐    ┌──────────────────────┐
│      SUPABASE        │    │       UPSTASH        │
│   (PostgreSQL)       │    │   (Redis)            │
│   500MB free         │    │   10k req/day free   │
└──────────────────────┘    └──────────────────────┘
```

---

## Request Lifecycle

```
┌──────┐     ┌──────┐     ┌──────┐     ┌──────┐     ┌──────┐
│Client│────>│Nginx │────>│Django│────>│Query │────>│View  │
│      │     │      │     │      │     │Set   │     │      │
└──────┘     └──────┘     └──────┘     └──────┘     └──────┘
                                 │           │           │
                                 │           │           │
                    ┌────────────┘     ┌─────┘     ┌─────┘
                    ▼                  ▼           ▼
              ┌──────────┐      ┌──────────┐  ┌──────────┐
              │ Tenant   │      │Tenant    │  │RBAC      │
              │Middleware │      │QuerySet  │  │Permission│
              │          │      │          │  │          │
              │ Resolve  │      │ Filter   │  │ Check    │
              │ request  │      │ by store │  │ JWT role │
              │ .store   │      │ _id      │  │          │
              └──────────┘      └──────────┘  └──────────┘
```
