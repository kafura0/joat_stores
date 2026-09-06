# JOAT Stores — API Reference

Base URL: `https://<your-api-url>/api/v1/`

All responses use the standard envelope format:
- **Single object:** `{ "data": { ... } }`
- **List:** `{ "data": [...], "meta": { "count": N, "next": "cursor", "previous": null } }`
- **Validation error (422):** `{ "errors": [{ "field": "phone", "message": "...", "code": "INVALID_PHONE" }] }`
- **Non-field error (400/403/404):** `{ "errors": [{ "field": null, "message": "...", "code": "STORE_NOT_FOUND" }] }`

---

## Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/token/` | Login — returns access token in body, refresh token in httpOnly cookie |
| POST | `/auth/token/refresh/` | Refresh access token — reads refresh from cookie, rotates both tokens |
| POST | `/auth/logout-all/` | Invalidate all refresh tokens for the authenticated user |
| POST | `/auth/google/callback/` | Google OAuth2 PKCE callback — exchange code for JWT |

---

## Platform Admin — Store Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/platform/stores/` | Provision a new store (atomic: store + subscription + owner) |
| GET | `/platform/stores/list/` | List all stores (paginated) |
| PATCH | `/platform/stores/{id}/status/` | Update store status (pending→active→suspended→cancelled) |

---

## Platform Admin — Subscriptions

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/platform/subscriptions/` | List all subscriptions (filterable by `?status=`) |
| GET | `/platform/subscriptions/{id}/` | Get subscription detail |
| PATCH | `/platform/subscriptions/{id}/` | Update subscription status or assign plan |

---

## Platform Admin — Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/platform/analytics/gmv/` | Platform-wide GMV (KES + USD). Query: `?start=&end=` |
| GET | `/platform/analytics/unit-economics/` | Cost per tenant, revenue per tenant |
| GET | `/platform/analytics/tenant-health/` | Tenant health snapshots. Query: `?date=yesterday` |
| GET | `/platform/stores/{id}/first-order/` | First order milestone for a store |

---

## Store — Branding & Settings

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/store/branding/` | Public | Store branding (colours, logo, tagline). Returns 503 if suspended |
| GET | `/store/themes/` | Store staff | Get current theme design tokens |
| PATCH | `/store/themes/` | Store manager | Update theme tokens |
| GET | `/store/themes/presets/` | Public | List available theme presets |
| POST | `/store/themes/apply-preset/` | Store manager | Apply a theme preset by slug |
| GET | `/store/offline-snapshot/` | Public | PWA offline inventory snapshot |

---

## Store — Logo Upload

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/store/settings/logo/` | Store manager | Upload logo file. Accepts multipart form with `logo` field (image). Compresses to WebP, saves to MEDIA_ROOT/logos/. Returns `{ data: { logo_url: "..." } }` |

---

## Products — Categories

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/store/categories/` | List categories (paginated, ordered by position) |
| POST | `/store/categories/` | Create category |
| GET | `/store/categories/{id}/` | Retrieve category |
| PUT | `/store/categories/{id}/` | Full update category |
| PATCH | `/store/categories/{id}/` | Partial update category |
| DELETE | `/store/categories/{id}/` | Delete category |

---

## Products — Products

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/store/products/` | List products (paginated, only available) |
| POST | `/store/products/` | Create product |
| GET | `/store/products/{id}/` | Retrieve product with nested variants + images |
| PUT | `/store/products/{id}/` | Full update product |
| PATCH | `/store/products/{id}/` | Partial update product |
| DELETE | `/store/products/{id}/` | Delete product |
| GET | `/store/products/{id}/qr/` | Generate product QR code as PNG |

---

## Products — Variants

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/store/variants/` | List variants (filterable by `?product=`) |
| POST | `/store/variants/` | Create variant |
| GET | `/store/variants/{id}/` | Retrieve variant |
| PUT | `/store/variants/{id}/` | Full update variant |
| PATCH | `/store/variants/{id}/` | Partial update variant |
| DELETE | `/store/variants/{id}/` | Delete variant |

---

## Products — Images

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/store/product-images/` | List product images |
| POST | `/store/product-images/` | Upload image (auto-compressed to WebP ≤ 800KB) |
| GET | `/store/product-images/{id}/` | Retrieve product image |
| PUT | `/store/product-images/{id}/` | Full update |
| PATCH | `/store/product-images/{id}/` | Partial update |
| DELETE | `/store/product-images/{id}/` | Delete product image |

---

## Products — Import

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/store/products/import/` | Store manager | Import products from CSV. Accepts multipart form with `file` field. Optional `category` param to assign all imported products to a category. Returns `{ data: { imported: N, errors: [...] } }` |
| GET | `/store/products/import/template/` | Store manager | Download CSV template for import |

---

## Orders — Cart

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/store/cart/` | Retrieve cart from Redis. Query: `?cart_ref=<ref>` |
| POST | `/store/cart/` | Add item (product_id, variant_id, quantity) |
| DELETE | `/store/cart/` | Remove item by variant_id |
| POST | `/store/cart/merge/` | Merge guest cart into authenticated user cart |

---

## Orders — Checkout & Orders

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/store/checkout/` | Guest checkout: validate cart, create order, initiate M-Pesa STK Push |
| GET | `/store/orders/` | List orders (filterable by `?status=` and `?payment_method=`) |
| GET | `/store/orders/{id}/` | Retrieve order detail |
| GET | `/store/orders/{id}/status/` | Lightweight order status polling (no auth) |
| POST | `/store/orders/{id}/confirm/` | Staff: confirm pending order |

---

## Orders — Dashboard & Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/store/dashboard/` | Merchant dashboard stats (revenue, transactions, products, low stock, recent orders, top products) |
| GET | `/store/customers/` | List customers (searchable by name/email) |
| POST | `/store/customers/` | Create customer |
| GET | `/store/customers/{id}/` | Retrieve customer with order stats |
| GET | `/store/inventory/` | List stock levels (filterable by `?search=` and `?status=`) |
| GET | `/store/users/` | List staff members |
| POST | `/store/users/` | Create staff member |

---

## Orders — Coupons

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/store/coupons/` | Store manager | List all coupons |
| POST | `/store/coupons/` | Store manager | Create coupon (percentage or fixed discount) |
| GET | `/store/coupons/{id}/` | Store manager | Get coupon detail |
| PUT/PATCH | `/store/coupons/{id}/` | Store manager | Update coupon |
| DELETE | `/store/coupons/{id}/` | Store manager | Delete coupon |
| POST | `/store/coupons/validate/` | Public | Validate coupon code. Body: `{ "code": "...", "order_total": 1000 }`. Returns discount details |

---

## Staff Management

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/users/` | Store owner/manager | List all users for the store |
| POST | `/users/` | Store owner | Create new staff user |
| GET | `/users/{id}/` | Store owner/manager | Get user detail |
| PATCH | `/users/{id}/` | Store owner | Update user (role, name, email) |
| DELETE | `/users/{id}/` | Store owner | Deactivate user |

---

## Loyalty

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/store/loyalty/accounts/` | Store manager | List loyalty accounts |
| GET | `/store/loyalty/accounts/{id}/` | Store manager | Get loyalty account detail with transaction history |
| GET | `/store/loyalty/stamp-cards/` | Store manager | List stamp cards |
| POST | `/store/loyalty/stamp-cards/` | Store manager | Create stamp card |
| GET | `/store/loyalty/stamp-cards/{id}/` | Store manager | Get stamp card detail |
| PUT/PATCH | `/store/loyalty/stamp-cards/{id}/` | Store manager | Update stamp card |
| POST | `/store/loyalty/redeem/` | Store manager | Redeem points for reward |
| GET | `/store/loyalty/check/` | Public | Check loyalty points by phone number. Query: `?phone=...` |

---

## Payments

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/payments/initiate-stk/` | Initiate M-Pesa STK Push for checkout |
| POST | `/payments/mpesa-callback/` | Daraja webhook (public, HMAC verified) |
| POST | `/payments/{id}/reverse/` | Queue M-Pesa reversal (store manager only) |
| POST | `/payments/card/initiate/` | Stripe card payment scaffold (returns 501) |
| POST | `/payments/stripe-webhook/` | Stripe webhook (public, signature verified) |

---

## Payments — C2B

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/payments/c2b-register/` | Store manager | Register C2B callback URLs with Safaricom |
| POST | `/payments/c2b-callback/` | Public (webhook) | Receive C2B payment notification from Safaricom |
| POST | `/payments/c2b-validation/` | Public (webhook) | Validate incoming C2B payment |

---

## Restaurant — Menu Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/restaurant/menu-sections/` | List menu sections (ordered by position) |
| POST | `/restaurant/menu-sections/` | Create menu section |
| GET/PUT/PATCH/DELETE | `/restaurant/menu-sections/{id}/` | CRUD on menu section |
| GET | `/restaurant/menu-items/` | List menu items (filtered by time-based availability) |
| POST | `/restaurant/menu-items/` | Create menu item |
| GET/PUT/PATCH/DELETE | `/restaurant/menu-items/{id}/` | CRUD on menu item |
| GET | `/restaurant/modifier-groups/` | List modifier groups |
| POST | `/restaurant/modifier-groups/` | Create modifier group |
| GET/PUT/PATCH/DELETE | `/restaurant/modifier-groups/{id}/` | CRUD on modifier group |
| GET | `/restaurant/modifiers/` | List modifiers |
| POST | `/restaurant/modifiers/` | Create modifier |
| GET/PUT/PATCH/DELETE | `/restaurant/modifiers/{id}/` | CRUD on modifier |

---

## Restaurant — Tables & Sessions

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/restaurant/tables/` | List tables |
| POST | `/restaurant/tables/` | Create table |
| GET/PUT/PATCH/DELETE | `/restaurant/tables/{id}/` | CRUD on table |
| POST | `/restaurant/tables/{id}/qr-token/` | Generate HMAC-signed QR token |
| GET | `/restaurant/sessions/` | List table sessions |
| POST | `/restaurant/sessions/` | Open session (enforces one-OPEN-per-table) |
| GET | `/restaurant/sessions/{id}/` | Retrieve session |
| PATCH | `/restaurant/sessions/{id}/assign-waiter/` | Assign waiter |
| PATCH | `/restaurant/sessions/{id}/request-bill/` | OPEN → BILL_REQUESTED |
| PATCH | `/restaurant/sessions/{id}/close/` | BILL_REQUESTED → CLOSED |
| GET | `/restaurant/sessions/{id}/bill/` | Get itemized bill |
| POST | `/restaurant/sessions/{id}/pay-bill/` | Single-payer bill settlement via M-Pesa |
| POST | `/restaurant/sessions/{id}/split-bill/` | Split bill across multiple payers |

---

## Restaurant — Orders & Kitchen

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/restaurant/public-menu/` | Public menu (no auth) — available items per section |
| POST | `/restaurant/orders/` | Place dine-in order (creates order + kitchen ticket) |
| POST | `/restaurant/orders/takeaway/` | Place takeaway order |
| POST | `/restaurant/orders/takeaway/{id}/pay/` | Initiate payment for takeaway |
| GET | `/restaurant/orders/{id}/status/` | Customer order status polling (no auth) |
| GET | `/restaurant/kitchen/tickets/` | Kitchen display: PENDING + IN_PROGRESS tickets |
| PATCH | `/restaurant/kitchen/tickets/{id}/` | Update ticket status (IN_PROGRESS/COMPLETED/CANCELLED) |

---

## Restaurant — Reservations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/restaurant/reservations/` | List reservations |
| POST | `/restaurant/reservations/` | Create reservation |
| GET | `/restaurant/reservations/{id}/` | Retrieve reservation |
| PATCH | `/restaurant/reservations/{id}/confirm/` | PENDING → CONFIRMED |
| PATCH | `/restaurant/reservations/{id}/seat/` | CONFIRMED → SEATED (auto-creates TableSession) |
| PATCH | `/restaurant/reservations/{id}/no-show/` | CONFIRMED → NO_SHOW |

---

## Restaurant — Pending Orders (Pre-Arrival)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/restaurant/pending-orders/` | Create PendingOrder (returns 6-digit PIN) |
| GET | `/restaurant/pending-orders/lookup/` | Waiter lookup by PIN or phone |
| POST | `/restaurant/pending-orders/{id}/pay/` | Advance payment for PendingOrder |
| POST | `/restaurant/pending-orders/{id}/convert/` | Convert to DineInOrder + KitchenTicket |

---

## Restaurant — QR & Fallbacks

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/restaurant/qr/validate/?token=<token>` | Validate QR token (returns table details + confirmation prompt) |
| GET | `/t/{table_id}/` | Public table info for wrong-table QR fallback |

---

## Bar — Tabs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/bar/tabs/` | List open tabs |
| POST | `/bar/tabs/` | Open new tab |
| GET | `/bar/tabs/{id}/` | Full tab detail with rounds + items |
| POST | `/bar/tabs/{id}/rounds/` | Add round (enforces age restriction, applies happy hour) |
| DELETE | `/bar/tabs/{id}/items/{item_id}/` | Remove item (audit trail) |
| POST | `/bar/tabs/{id}/request-bill/` | OPEN → BILL_REQUESTED |
| POST | `/bar/tabs/{id}/split/` | Split tab across payers |

---

## Bar — Happy Hours

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/bar/happy-hours/` | List happy hour windows |
| POST | `/bar/happy-hours/` | Create happy hour window |

---

## Contracting — Services & Bookings

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/contracting/services/` | List active services (public) |
| POST | `/contracting/services/` | Create service (store manager) |
| GET | `/contracting/services/{id}/` | Service detail (public) |
| GET | `/contracting/services/{id}/availability/` | Available slots (next 30 days) |
| GET | `/contracting/bookings/` | List bookings |
| POST | `/contracting/bookings/` | Create booking (marks slot as booked) |
| PATCH | `/contracting/bookings/{id}/confirm/` | Confirm booking |

---

## Contracting — Quotes & Jobs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/contracting/quote-requests/` | List quote requests |
| POST | `/contracting/quote-requests/` | Submit quote request |
| POST | `/contracting/quote-requests/{id}/quote/` | Create quote in response |
| PATCH | `/contracting/quotes/{id}/accept/` | Accept quote (auto-creates Job) |
| PATCH | `/contracting/quotes/{id}/reject/` | Reject quote |
| GET | `/contracting/jobs/{id}/` | Retrieve job with milestones |
| PATCH | `/contracting/jobs/{id}/transition/` | Transition job status |
| PATCH | `/contracting/milestones/{id}/` | Update milestone + upload photo |

---

## Contracting — Invoices

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/contracting/jobs/{id}/invoice/` | Create invoice for completed job |
| GET | `/contracting/invoices/{token}/download/` | Download invoice PDF (public, HMAC token) |
| POST | `/contracting/invoices/{id}/pay/` | Initiate M-Pesa payment |

---

## Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/analytics/summary/` | Pre-aggregated daily summary. Query: `?date=yesterday` |
| GET | `/analytics/events/` | AI event list (platform admin) |
| GET | `/analytics/restaurant/peak-hours/` | 24-slot hourly breakdown (past 7 days) |
| GET | `/analytics/restaurant/table-turn-rate/` | Average table turn rate (7 days) |
| GET | `/analytics/bar/tab-metrics/` | Tab completion rate, avg round size (7 days) |
| GET | `/analytics/bar/occupancy/` | Days with at least one open tab (7 days) |
| GET | `/analytics/export/csv/` | Export DailyRevenueSummary as CSV |

---

## SaaS — Plans & Subscriptions

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/saas/plans/` | List active public plans |
| POST | `/saas/plans/` | Create plan (platform admin) |
| GET | `/saas/plans/{id}/` | Plan detail |
| GET | `/saas/subscription/` | Current store's subscription + plan |
| POST | `/saas/subscription/renew/` | Initiate M-Pesa STK Push for renewal |

---

## AI

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/ai/events/` | Capture behavioral event (returns 202, non-blocking) |
| GET | `/ai/recommendations/` | Product recommendations (requires Growth/Pro plan) |
| GET | `/ai/predictions/peak-hours/` | Tomorrow's peak hour forecast |
| POST | `/ai/search/` | Natural language menu search |

---

## Loyalty

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/loyalty/account/` | Points balance. Query: `?phone=` |
| GET | `/loyalty/history/` | Points ledger (last 50 transactions). Query: `?phone=` |
| POST | `/loyalty/redeem/` | Redeem points at checkout |
| GET | `/loyalty/stamp-cards/` | List active stamp cards |
| POST | `/loyalty/stamp-cards/` | Create stamp card (store staff) |
| GET | `/loyalty/my-stamp-cards/` | Customer's stamp card progress. Query: `?phone=` |
| GET | `/loyalty/customers/` | All customer profiles (store staff) |
| GET | `/loyalty/customers/{phone}/` | Single customer profile by phone |

---

## Notifications — WhatsApp

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/notifications/whatsapp/inbound/` | Meta webhook verification (hub.challenge) |
| POST | `/notifications/whatsapp/inbound/` | WhatsApp inbound message webhook |

---

## Customer Hub (Cross-Tenant)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/hub/auth/register/` | Register PlatformUser account (cross-tenant) |
| POST | `/hub/auth/login/` | Login with email/password |
| GET | `/hub/me/` | Get authenticated user profile |
| GET | `/hub/stores/` | Stores the customer has engaged with |
| GET | `/hub/orders/` | Cross-store order history (last 100) |
| GET | `/hub/loyalty/` | Cross-store loyalty summary |
| POST | `/hub/fcm/register/` | Register FCM device for push notifications |
| POST | `/hub/fcm/unregister/` | Deactivate FCM device |

---

## Infrastructure

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health/` | Health check (no DB, no auth) |
| GET | `/health/workers/` | Celery worker health (queue depths + heartbeats). 503 if degraded |
| GET | `/schema/` | OpenAPI schema download (DRF Spectacular) |
| GET | `/docs/` | Swagger UI interactive docs |

---

## Endpoint Summary

| App | Endpoint Count |
|-----|----------------|
| Root / Infrastructure | 4 |
| Users / Auth | 4 |
| Store (platform + storefront) | 9 |
| Product | 26 |
| Order / Cart / Checkout | 16 |
| Payment | 5 |
| Restaurant | 48 |
| Bar | 9 |
| Contracting | 18 |
| Analytics | 11 |
| SaaS | 8 |
| AI | 4 |
| Loyalty | 8 |
| Notifications | 2 |
| Customer Hub | 8 |
| **Total** | **~180** |

---

## Internal — Cron Trigger

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/internal/run-cron/` | Bearer token (`CRON_SECRET`) or QStash signature | Trigger a cron task. Body: `{"task": "heartbeat" \| "warm_branding_cache" \| "check_low_stock"}` |

Used by Upstash QStash to trigger scheduled tasks on Render free tier (no Celery Beat needed).
