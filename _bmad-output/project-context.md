---
project_name: 'joat_stores'
user_name: 'KAFURAHA'
date: '2026-02-25'
status: 'complete'
optimized_for_llm: true
rule_count: 140+
sections_completed:
  - technology_stack
  - language_rules
  - framework_rules
  - testing_rules
  - quality_rules
  - workflow_rules
  - critical_dont_miss
  - b2b2c_architecture
  - merchant_onboarding
  - ai_scaffold
  - analytics_capture
  - fab_module
  - mpesa_deep_rules
  - order_state_machine
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

### Backend
- Python 3.14.3
- Django 5.2 LTS + Django REST Framework
- djangorestframework-simplejwt (JWT auth, custom store_id claim)
- django-allauth (Google Sign-In / social auth)
- django-safedelete (soft delete + DPA-compliant anonymisation)
- django-encrypted-fields (PII field-level encryption)
- django-cors-headers
- django-filter + DRF SearchFilter
- django-environ (.env config management)
- Celery 5.6.2 + Redis 8.6 (async worker + broker)
- PostgreSQL 17.x (primary DB)
- structlog (structured logging with PII scrubber)
- Pillow (server-side WebP image compression)
- Sentry SDK (error monitoring)
- pytest + factory-boy (testing)
- flake8 + black + isort (linting/formatting)

### Frontend (storefront + admin — two separate Next.js apps)
- Next.js 16.x (App Router)
- TypeScript (strict mode — no `any` without justification comment)
- Tailwind CSS
- TanStack Query / React Query (server state)
- Zustand (UI state)
- react-hook-form + zod (forms + validation)
- axios (API client with auth interceptor)
- pino (structured logging)

### Infrastructure
- Docker Compose (single-file orchestration — no Kubernetes at MVP)
- Nginx (reverse proxy + per-tenant domain routing)
- Redis AOF persistence enabled (cart data survives container restart)
- GitHub Actions (CI: lint + test; CD: SSH deploy on merge to main)
- Celery Flower (queue monitoring — Docker service)

## Critical Implementation Rules

### Language-Specific Rules

#### Python (Django backend)
- All settings split across `config/settings/base.py`, `local.py`, `production.py` — never add config to a single `settings.py`
- All credentials via `django-environ` — never hardcode secrets; all env vars named `SCREAMING_SNAKE_CASE`
- Use `structlog` for all backend logging — never `print()` or bare `logging.info()`
- PII (phone, email) must be masked in all log output via structlog PII scrubber processor
- Phone normalisation: always call `normalise_mpesa_phone()` from `core/utils.py` — never inline in views or serializers
- Money: always `DecimalField(max_digits=10, decimal_places=2)` — never `FloatField` or Python `float`
- Datetimes: always ISO 8601 UTC in DB and API (`"2026-02-24T12:00:00Z"`) — never Unix timestamps
- Soft delete: use `django-safedelete` — never override `delete()` manually
- PII encryption: use `django-encrypted-fields` at field level — never encrypt in serializer logic

#### TypeScript (Next.js frontend)
- Strict mode enforced — no `any` types without an explicit justification comment on the same line
- Interfaces prefixed `I` (`IProduct`, `IOrder`, `ICartItem`) — types are plain PascalCase (`OrderStatus`, `ProductVariant`)
- All shared types live in `types/index.ts` — never define types inline in component files
- Zustand stores named `use{Domain}Store` (`useCartStore`, `useAuthStore`)
- TanStack Query keys always arrays with domain prefix: `['products', storeId]`, `['order', orderId]`
- `formatCurrency` and `formatDate(Africa/Nairobi)` utilities live in `lib/utils.ts` — never format inline
- JWT: access token in memory, refresh token in httpOnly cookie — never `localStorage` for tokens
- Do not use `next-auth` — conflicts with custom `store_id` JWT claim; auth is custom via `lib/auth.ts`

### Framework-Specific Rules

#### Django / DRF (backend)
- Every tenant model MUST inherit `TenantModel` from `core/models.py` — never `models.Model` directly
- Every tenant viewset MUST inherit `TenantViewSet` from `core/views.py` — never `viewsets.ModelViewSet` directly
- Every tenant serializer MUST inherit `TenantSerializer` — auto-injects `store` from request; never set `store` manually in a view
- Tenant isolation enforced at 5 layers — middleware → TenantQuerySet → TenantSerializer → IsStoreScoped → StoreAdmin; all 5 must be present for any new domain app
- `request.store` is resolved by `TenantMiddleware` from hostname or `X-Store-ID` header — never resolve tenant manually in a view
- Pagination: always use `StoreCursorPagination` — never `PageNumberPagination`; no unbounded list endpoints
- Custom exception handler in `core/exceptions.py` produces `{errors:[{field, message, code}]}` — never override per-view
- Rate limits read from `request.store.subscription.plan` — never hardcode rate limit values
- `django-allauth` + `simplejwt` integration: allauth creates Django user; custom `SocialAccountAdapter` calls simplejwt to issue JWT with `store_id` claim — must be a dedicated sub-task, not assumed automatic
- Tenant type gates: `request.store.tenant_type in ['restaurant', 'bar']` for F&B; `request.store.tenant_type == 'bar'` for bar-only routes

#### Next.js App Router (frontend — both storefront and admin)
- Default to Server Components — only add `'use client'` for interactive islands (cart drawer, checkout form, kitchen poll, auth modals, variant selector, modifier modal)
- `middleware.ts` resolves tenant from hostname and sets context — never resolve tenant in a page component
- Kitchen order list polls every 5s via `refetchInterval: 5000` in TanStack Query — never use `setInterval` manually
- All API calls go through the `axios` instance in `lib/api.ts` (includes auth interceptor + token refresh) — never use `fetch` directly
- Auth guard for admin: `middleware.ts` checks JWT role claim — `platform_admin` token gets broader queryset scope
- Per-tenant theming via CSS variables set by `TenantThemeProvider` from hostname context — never hardcode brand colours in components
- `(store)` and `(restaurant)` are App Router route groups — do not confuse with actual URL segments
- Admin route groups: `(store-admin)` for store-scoped views, `(platform-admin)` for platform admin — RBAC-gated at middleware

### Testing Rules

#### Backend (pytest)
- Test files live in `apps/{domain}/tests/` — each app has `test_models.py`, `test_views.py`, `test_tasks.py` minimum
- Use `factory-boy` for all test fixtures — never create model instances with raw `Model.objects.create()` in tests
- Every test touching tenant data MUST include `store_id` scope — a tenant isolation failure is a build-breaking error
- Cross-tenant isolation test suite lives in `apps/store/tests/test_middleware.py` — run with `pytest -k "cross_tenant"` before any PR touching models or views
- Celery tasks: test with `task.apply()` (synchronous) in unit tests; use `@override_settings(CELERY_TASK_ALWAYS_EAGER=True)` for integration tests
- M-Pesa / Daraja: always mock the Daraja HTTP client in tests — never make live STK Push calls in CI
- Payment webhook tests: use signed payloads matching Daraja callback format — test both valid and tampered signatures
- Never assert on log output — use `structlog.testing.capture_logs()` if log content must be verified

#### Frontend (Next.js)
- No frontend test framework prescribed at MVP — document when added
- Component tests (when added): co-locate with component file as `ComponentName.test.tsx`
- TanStack Query: wrap test renders in `QueryClientProvider` with a fresh `QueryClient` per test
- Mock `lib/api.ts` axios instance — never make real HTTP calls in component tests
- Zustand stores: reset state between tests using `store.setState(initialState)`

### Code Quality & Style Rules

#### Naming Conventions

**Database:**
- Table names: Django default `{app}_{model}` snake_case plural (`store_product`, `order_orderitem`)
- Column names: snake_case always (`store_id`, `created_at`, `is_active`)
- Foreign keys: `{model}_id` suffix (`store_id`, `product_id`)
- Indexes: `idx_{table}_{column(s)}` (`idx_store_product_slug`)
- Unique constraints: `uq_{table}_{column(s)}` (`uq_store_slug`)
- Anti-pattern: never `userId`, `StoreID`, or mixed casing in DB columns

**API:**
- Resources: plural noun, lowercase, hyphenated (`/api/v1/products/`, `/api/v1/order-items/`)
- Nested resources: max 2 levels deep (`/api/v1/products/{id}/variants/`)
- Non-CRUD actions: POST to `/{resource}/{id}/{action}/` (`/api/v1/orders/{id}/confirm/`)
- Query params: snake_case (`?category_id=2&page_size=20`)
- Always `/api/v1/` prefix — never unversioned or `/v1/api/`
- Anti-pattern: never RPC-style (`/api/v1/getProduct/`) or singular resource (`/api/v1/product/`)

**Code:**
- Django models: PascalCase singular (`Product`, `OrderItem`, `StoreSubscription`)
- Django apps: snake_case singular domain (`store`, `product`, `order`, `payment`, `restaurant`, `bar`)
- Python functions/methods: snake_case verbs (`get_active_products()`, `send_confirmation()`)
- Django views/serializers: `{Model}{Action}View/Serializer` (`ProductListView`, `OrderCreateSerializer`)
- Celery tasks: `{verb}_{noun}` in `tasks.py` (`send_order_confirmation`, `trigger_low_stock_alert`)
- React components: PascalCase (`ProductCard`, `CartDrawer`, `KitchenOrderList`)
- React files: PascalCase `.tsx` (`ProductCard.tsx`) — except Next.js route files (lowercase `page.tsx`, `layout.tsx`)
- Environment variables: SCREAMING_SNAKE_CASE (`DJANGO_SECRET_KEY`, `MPESA_CONSUMER_KEY`)

#### Linting & Formatting
- Backend: `flake8` + `black` + `isort` enforced pre-merge via CI — no exceptions
- Frontend: TypeScript strict mode — `noImplicitAny`, no suppression without comment
- All Celery tasks in `apps/{domain}/tasks.py` — never define tasks inside views or serializers

#### API Response Format (non-negotiable)
- Single object: `{ "data": { ... } }`
- List: `{ "data": [...], "meta": { "count": N, "next": "cursor", "previous": null } }`
- Validation error (422): `{ "errors": [{ "field": "phone", "message": "...", "code": "INVALID_PHONE" }] }`
- Non-field error (400/403/404): `{ "errors": [{ "field": null, "message": "...", "code": "STORE_NOT_FOUND" }] }`
- Anti-pattern: never `{"error": "..."}`, never HTTP 200 with error content

#### Data Formats
- Money: string, 2 decimal places (`"1500.00"`) — never float
- Phone (M-Pesa): E.164 (`"+254712345678"`)
- Datetime: ISO 8601 UTC (`"2026-02-24T12:00:00Z"`) — never Unix timestamps
- Boolean: JSON native `true`/`false` — never `1`/`0`
- Null fields: always include as `null` — never omit absent optional fields
- IDs: integer DB PK — never UUID at MVP
- Tenant type enum: `"retail"`, `"restaurant"`, `"bar"` (lowercase)
- Order status enum: `"pending"`, `"confirmed"`, `"fulfilled"`, `"completed"`, `"cancelled"` (lowercase)

### Development Workflow Rules

#### Git & CI/CD
- CI runs on every PR: `flake8` + `black` + `isort` (backend), TypeScript strict compile (frontend), `pytest` full suite
- `pytest -k "cross_tenant"` must pass before any PR touching models, views, or Celery tasks that access tenant data
- CD: GitHub Actions deploys via SSH on merge to `main` — `scripts/deploy.sh` runs `git pull → docker compose pull → docker compose up -d`
- Never push directly to `main` — all changes via PR
- Branch naming: `feat/`, `fix/`, `chore/` prefix required (e.g. `feat/mpesa-webhook`, `fix/cart-isolation`, `chore/update-deps`)

#### VPS Deployment (critical constraint)
- Run `scripts/preflight.sh` before every `docker compose up` — checks ports 80/443/5432/6379 and existing container conflicts
- Pre-flight failure is a **hard stop** — do not proceed with `docker compose up` until all conflicts are resolved manually
- Existing live services on the VPS must not be disrupted — Docker network isolation is mandatory
- All services defined in a single `docker-compose.yml` with production overrides in `docker-compose.prod.yml`
- No Kubernetes, no managed cloud services at MVP — Docker Compose only
- Django migrations run automatically via container entrypoint on `docker compose up` — **never** run `manage.py migrate` manually against the production DB

#### Environment Configuration
- All secrets in `.env` files, loaded via `django-environ` — never committed to git
- Use `.env.example` as the canonical reference for all required variables
- Daraja M-Pesa credential swap (sandbox → production): change `MPESA_CONSUMER_KEY`, `MPESA_CONSUMER_SECRET`, `MPESA_SHORTCODE`, `MPESA_PASSKEY` in `backend/.env` — no code change required; verify swap by hitting `/api/v1/payments/mpesa-status/` health endpoint after restart
- Settings split: `DJANGO_SETTINGS_MODULE=config.settings.local` (dev), `config.settings.production` (prod)

#### Celery Task Standards (all tasks must follow this pattern)
```python
@shared_task(bind=True, max_retries=5, default_retry_delay=60, queue='order.notifications')
def send_order_confirmation(self, order_id: int) -> None:
    try:
        order = Order.objects.get(id=order_id)
        # ... task logic
    except Order.DoesNotExist:
        return  # Do not retry — object deleted
    except ExternalServiceError as exc:
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```
- Queue names: `order.notifications`, `inventory.alerts`, `billing.reminders`, `payments.reconciliation`, `analytics.reports`
- Dead-letter queue (DLQ) must be configured before writing any async task
- Monitor via Celery Flower Docker service — `/health/workers/` endpoint must be live

#### Backup
- `scripts/backup.sh` runs daily via Celery Beat: `pg_dump` → `/backups/$(date).sql.gz`, 7-day rotation
- Redis AOF persistence enabled in Docker Compose — cart data survives container restart

### Critical Don't-Miss Rules

#### Tenant Isolation (non-negotiable — any violation is a data breach)
- NEVER use `models.Model` directly for any model that belongs to a tenant — always `TenantModel`
- NEVER use `viewsets.ModelViewSet` directly — always `TenantViewSet`
- NEVER filter by `store_id` manually in a view — `TenantQuerySet` handles this automatically; manual filtering is a sign the base class is missing
- NEVER return cross-tenant data in any endpoint — `pytest -k "cross_tenant"` catches this; run it before every PR
- Analytics models are tenant-scoped — `DailyRevenueSummary`, `TopProduct`, `TenantHealthSnapshot` all inherit `TenantModel` + `TenantViewSet`; there is no "platform-level" analytics model; platform admin views use `IsPlatformAdmin` permission, not a bypass of tenant scoping
- Never use `Model.all_objects` without explicitly adding `.filter(store=request.store)` — `all_objects` (django-safedelete) bypasses `TenantQuerySet` and leaks cross-tenant soft-deleted records

#### M-Pesa / Daraja
- NEVER normalise phone numbers inline — always use `normalise_mpesa_phone()` from `core/utils.py`
- NEVER store money as float — `DecimalField(max_digits=10, decimal_places=2)` only
- NEVER call Daraja API directly from a view — always via `apps/payment/daraja.py` client
- NEVER trust an STK Push callback without signature verification — tampered webhook = silent payment fraud
- Daraja sandbox credentials must be in `.env` from day one — never hardcode
- Never call `.delay()` before a DB transaction commits — always use `transaction.on_commit(lambda: task.delay(...))` for any task triggered by a model save or status change

#### Frontend Performance (3G mobile-first)
- NEVER add `'use client'` to a component unless it genuinely requires browser interactivity — Server Components are the default
- NEVER use `setInterval` for polling — use TanStack Query `refetchInterval`
- NEVER use `fetch` directly — all HTTP via the `axios` instance in `lib/api.ts`
- NEVER store JWT access token in `localStorage` — memory only; refresh token in httpOnly cookie
- Store only the WebP-compressed output — never retain the original uploaded file after Pillow processing; delete original from temp storage immediately after compression

#### API Contract
- NEVER return bare objects or custom envelope shapes — always `{data}`, `{data, meta}`, or `{errors}`
- NEVER return HTTP 200 with error content — use 400/422/403/404 correctly
- NEVER create unbounded list endpoints — all lists use `StoreCursorPagination`
- NEVER use floats for money in API responses — always string `"1500.00"`

#### Architecture Sequence (implementation order matters)
- `core/` must be fully implemented BEFORE any domain app (`store`, `product`, `order`, etc.)
- Tenant middleware must exist before any business model is created
- Celery DLQ must be configured before any async task is written
- `store_id` JWT claim must be established before any storefront or admin auth flow is built
- Tenant type (`retail` / `restaurant` / `bar`) is locked after first order — schema must accommodate this from the start; never write a migration or admin action that changes `store.tenant_type` on a store with existing orders
- Bar module requires both `apps/restaurant/` and `apps/bar/` active — never implement bar features without the restaurant module present

#### Common Misinterpretations
- Many-to-many `through` models joining two tenant-scoped models must also inherit `TenantModel` — a through model with `models.Model` has no `store_id` and can produce cross-tenant join results
- All list endpoints paginate — including internal admin autocomplete, dropdown, and search endpoints — no exceptions for "internal" endpoints
- Never add `'use client'` to layout files or parent wrapper components — it makes every child a Client Component by inheritance; use React Context only within a `'use client'` island boundary
- Never call `.delay()` inside utility functions — task dispatch must always happen at the call site where the transaction context is known, so `transaction.on_commit` can be applied correctly

#### Edge Cases Agents Must Not Miss
- `store_id` claim is `null` for platform-level requests and during user registration — always guard with `if request.store` before accessing tenant context; never assume it is always populated
- `preflight.sh` is mandatory before EVERY `docker compose up` — including `up --build`, `up -d`, and single-service restarts; not just full deploys
- Celery Beat must use `django-celery-beat` DB scheduler or mount `--schedule` file as a Docker volume — never rely on in-memory beat schedule that resets on container restart

#### B2B2C Architecture Rules

**Identity Layers — agents must never confuse these three:**

| Identity | Role Claim | `store_id` in JWT | `request.store` |
|---|---|---|---|
| Platform Admin | `platform_admin` | None | `None` |
| Merchant Staff | `store_owner` / `store_manager` | Their store | Populated |
| Customer | `customer` | Store they registered at | Populated |

**Customer Account Scoping:**
- Customer accounts are store-scoped — the same person at Store A and Store B = two separate `CustomUser` records with different `store_id`; this is by design
- Never `CustomUser.objects.filter(email=email)` without a `store_id` filter — this matches customers across tenants
- Google Sign-In at a storefront must produce a store-scoped customer account — `store_id` must be in scope during the OAuth callback; if missing, allauth creates a platform-level orphaned user
- Storefront login errors must always return generic "Invalid credentials" — never reveal whether the account exists on another store (information leak)

**Platform Admin Data Access:**
- Platform admin JWT has no `store_id` claim — `TenantMiddleware` sets `request.store = None`
- Platform admin data access uses dedicated `(platform-admin)` endpoints with explicit `?store_id=` param — never bypass `TenantViewSet` with a role check; a compromised platform admin token must not return cross-tenant data
- Platform admin endpoints use `IsPlatformAdmin` permission, not `IsStoreScoped` — these are mutually exclusive permission classes

**SaaS Billing:**
- `StoreSubscription` is platform-owned — queried without tenant scoping in `apps/saas/`; never accidentally apply `TenantQuerySet` to subscription queries
- M-Pesa subscription renewal is a separate STK Push flow from customer checkout — separate Daraja callback endpoint, separate Celery queue (`billing.reminders`)
- Never mix `apps/payment/Payment` (customer transactions) with `apps/saas/StoreSubscription` billing records — different models, different flows, different audit trails
- Store provisioning sequence is strict and must be followed in order: Create Store → assign domain → set `tenant_type` → create `StoreSubscription` → assign `store_owner` user — missing any step leaves the tenant in a broken state
- Third-merchant onboarding must complete in under 24 hours — core investor thesis validation metric; provisioning sequence must exist as a runbook

**Feature Flag & Plan Limit Enforcement:**
- Plan limit enforcement lives in `apps/saas/services.py` as a shared `enforce_plan_limit(store, feature, current_count)` function — both single-create AND bulk operations call the same function; never check limits only in individual views
- Plan limit exceeded response: HTTP 403 with `code: "PLAN_LIMIT_EXCEEDED"` and body `{"feature": "products", "limit": 100, "current": 100}` — never 402
- Feature flag format: `plan.features` JSON field — `{"has_analytics": true, "has_ai": false, "max_products": 100, "max_staff": 5, "api_rate_limit": 1000}`
- Feature flags enforced server-side on every request — never cache plan features in JWT or session; always read live from `request.store.subscription.plan`

**B2B2C Payment Idempotency:**
- STK Push initiation must be idempotent — check for existing `pending` or `confirmed` payment on the same order before initiating a new STK Push; return the existing payment record if found
- Subscription renewal STK Push is also idempotent — one active pending renewal per store at a time

**B2B2C Resilience Rules:**
- Cart retrieval failure must raise an explicit error — never `cart = cache.get(cart_key) or []`; if cart is `None` raise `CartUnavailableError` → 503 with `code: "CART_UNAVAILABLE"`; never proceed to order creation with an unverified cart
- Payment confirmation and order status update must be wrapped in `transaction.atomic()` — they are a single logical operation; if order status update fails, payment confirmation must roll back; the Celery task retries the entire atomic block
- Feature flag checks must be applied at order placement endpoints, not just resource creation endpoints — a merchant must not be able to place orders via a feature their plan no longer includes
- Platform admin customer search must never return results that link the same person across stores — search always scoped to a single `store_id` param; cross-store customer aggregation is prohibited under Kenya DPA 2019

**B2B2C Testing Rules:**
- Platform admin endpoint tests must assert that results include data from MULTIPLE stores — a test that only verifies single-store results on a platform admin endpoint is testing the wrong behaviour
- Customer account tests must verify that the same email at two different stores produces two isolated `CustomUser` records with no shared data

#### Security
- All credentials via environment variables — never hardcode in any file committed to git
- PII (phone, email) encrypted at rest via `django-encrypted-fields` — never store plain PII in non-encrypted fields
- All admin PII access must produce an audit log entry in `core/models.py` → `AdminPIIAccessLog(user, store, record_type, record_id, accessed_at)` — single model, not per-app — Kenya DPA 2019 compliance
- PII anonymisation on deletion means replacing name/phone/email with a hash or placeholder — not just setting `deleted_at`; `django-safedelete` hook triggers anonymisation automatically
- 72-hour breach notification window required under Kenya DPA 2019 — ensure incident response process exists before go-live
- Daraja webhook verification = HMAC signature check using `MPESA_PASSKEY` + timestamp hash — never just check `ResultCode == 0`; that is payload inspection, not signature verification
- `/api/v1/payments/mpesa-callback/` must be rate-limited at both Nginx level AND DRF throttle level — it is unauthenticated by IP and is a DDoS surface independent of subscription plan rate limits
- RBAC roles (`platform_admin`, `store_owner`, `store_manager`, `customer`) come from JWT `role` claim only — never `is_staff`, `is_superuser`, or Django group membership; Django's built-in permission system is bypassed entirely in favour of JWT claims
- `OWASP Top 10` + pen-test checklist required before production launch
- VPS must be Kenya/EAC-hosted for DPA 2019 compliance — never deploy to US/EU regions

#### Merchant Onboarding & Tenant Provisioning
- Entire provisioning sequence wrapped in `transaction.atomic()` — partial state is worse than no state; rollback everything if any step fails
- Provisioning sequence is strictly ordered: Create Store → Assign Domain → Set `tenant_type` → Create `StoreSubscription` → Assign `store_owner` user — never skip or reorder steps
- Pre-provisioning checks required before creating anything: domain not already assigned, slug globally unique, `tenant_type` is valid enum value
- Post-provisioning verification required: store resolves at domain → store_owner JWT contains correct `store_id` → `GET /api/v1/products/` returns empty list (not 403) for store_owner token
- Nginx config for new tenant manually added to `nginx/conf.d/tenants/` at MVP — only manual step; new tenant domains must use TTL ≤ 300s to meet 24-hour onboarding SLA
- `store.tenant_type` immutability enforced in `Store.save()` override — raise `IntegrityError` if `tenant_type` changes after first order exists; admin UI shows it as read-only post-first-order
- Platform admin customer search scoped to single `store_id` param — cross-store customer aggregation prohibited under Kenya DPA 2019

#### AI Scaffold (`apps/ai/`)
- `apps/ai/` exists from day one with `models.py`, `services.py`, `views.py` — all endpoints return `501 Not Implemented`, gated behind `plan.features.has_ai == True`
- Never import ML libraries (TensorFlow, PyTorch, scikit-learn) at MVP — `services.py` contains pure Python placeholder classes with `# TODO: Phase 3` comments only
- `AIEvent` model captures product views, cart adds/removes, searches, and order completions from day one — historical data must exist when the Phase 3 algorithm ships; it cannot be retroactively created
- `AIEvent` captures use `transaction.on_commit` — never inside a transaction; missed events are acceptable, corrupt events are not
- `AIEvent` is append-only — never update or delete events; incorrect events get a compensating new event
- All AI endpoints live in `apps/ai/urls.py` mounted at `/api/v1/ai/` — never scatter AI endpoints across domain apps
- Never use `AIEvent` data for business logic at MVP — instrumentation only; no order or payment flow may depend on it

#### Analytics Data Capture
- Analytics is a side effect, never a primary operation — use Django `post_save` signals + `transaction.on_commit` to trigger Celery tasks; never call analytics functions directly inside business logic
- Analytics dashboards show **yesterday's data** — Celery Beat runs `generate_daily_summary` at 00:05 daily; document this in admin UI copy; never promise real-time analytics
- Always read from pre-aggregated `DailyRevenueSummary` tables — never run live ORM aggregations (`Sum`, `Count`, `Avg`) on `Order` or `Payment` tables in a view; full table scans kill p95 at scale
- Analytics tasks are idempotent — use `update_or_create` on `(store, date)` composite key, never raw `create()`; safe to retry and re-run without duplicating data
- Analytics tasks run in `analytics.reports` queue — lowest priority; never share a queue with `order.notifications` or `payments.reconciliation`
- Platform GMV = sum of all tenant `DailyRevenueSummary.total_revenue` — never query raw `Order` table for platform-level aggregation
- F&B peak hours use hour-of-day bucketing (`DineInOrder.created_at__hour`) — requires a dedicated `HourlyOrderSummary(store, date, hour, order_count)` model; never stuff into `DailyRevenueSummary`
- Table turn rate captured on `TableSession.status = 'closed'` signal; bar tab completion rate and round size captured on `Tab.status = 'settled'` signal — never on individual item saves
- Missing analytics data after DLQ exhaustion is acceptable — analytics are non-critical; never let analytics task failures affect order processing queue health
- `TenantHealthSnapshot` is platform-level, runs as separate Celery Beat job, one snapshot per tenant per day — feeds investor unit economics dashboard; never expose raw snapshot data to store-level users

#### F&B Module — Restaurant & Bar

**Table Session State Machine:**
- Only one `OPEN` TableSession per table at a time — enforced at DB level with `UniqueConstraint(fields=['table', 'status'], condition=Q(status='open'))`; never rely on application-level checks only
- QR code encodes `store_id` + `table_id` + HMAC signature — never just `table_id`; unsigned QR allows anyone to join any table
- `TableSession` must be explicitly closed — never auto-close on payment; a table can have multiple payment rounds (split bills, added rounds)
- `TableSession` state machine: `OPEN → BILL_REQUESTED → CLOSED` — never skip `BILL_REQUESTED`

**Kitchen View:**
- `KitchenTicket` is created per order, not per item — modifiers denormalized into ticket JSON at creation time; kitchen view never joins `Product` or `ModifierGroup` tables
- `KitchenTicket` state transitions are one-directional: `PENDING → IN_PROGRESS → READY` — never go backwards; enforced in `KitchenTicket.transition(new_status)` method
- Kitchen view endpoint returns only `PENDING` and `IN_PROGRESS` tickets — `READY` tickets removed automatically; endpoint must complete in < 50ms (no multi-table joins)

**Modifier Groups:**
- `ModifierGroup` validation (min/max selections) happens server-side in serializer — never frontend-only
- Required modifier group (`min_selections > 0`) blocks submission: return 422 with `code: "MODIFIER_REQUIRED"`
- Modifier prices are additive to base item price: `total = item.base_price + sum(m.price for m in selected)`
- Modifier prices and item prices are **snapshotted** into `DineInOrderItem.modifiers_snapshot` at order time — never recalculate from current `Modifier.price` at payment time (prices may change)

**Bar Tab Rules:**
- `Tab.status` state machine: `OPEN → BILL_REQUESTED → SETTLED` — never skip states
- Age restriction: `MenuItem.is_age_restricted = True` requires `AgeRestrictionLog(staff_user, customer_approximate_age, verified_at)` entry before item can be added — legal compliance, not optional
- Happy hour pricing evaluated and **snapshotted** at item-add time — never recalculated at settlement

#### M-Pesa Deep Rules

**STK Push timeout handling:**
- Daraja times out after ~30s — webhook arrives with `ResultCode: 1032` (cancelled) or `ResultCode: 1037` (timeout)
- Timeout → payment status `EXPIRED`, order stays `PENDING`, customer sees retry prompt — never mark as `FAILED`
- `EXPIRED` payments never auto-retry — user must explicitly re-initiate STK Push

**Webhook deduplication:**
- `MpesaTransaction.mpesa_receipt_number` has `unique=True` DB constraint — duplicate webhook → catch `IntegrityError`, log, return HTTP 200 to Daraja; never return 4xx (causes Daraja to retry indefinitely)

**Reconciliation:**
- Celery Beat `reconcile_payments` runs daily — finds `STK_PUSH_INITIATED` payments older than 2 hours, queries Daraja Transaction Status API to resolve them
- Never trust webhook delivery alone — reconciliation is the mandatory safety net; both mechanisms must exist
- Reconciliation runs in `payments.reconciliation` queue — isolated from `order.notifications`

**Reversal:**
- M-Pesa reversal creates a new `Payment(type='REVERSAL')` linked to original — never mutate original `Payment` record; full audit trail required
- Reversal only possible within 24 hours — enforce before calling Daraja API; return 422 with `code: "REVERSAL_WINDOW_EXPIRED"` if exceeded

**Daraja token caching:**
- Cache Daraja OAuth2 access token in Redis: key `daraja:access_token:{env}`, TTL 3500s — never fetch a new token per STK Push call; adds ~200ms latency and risks Daraja rate limiting

#### Order & Checkout State Machine

**Valid transitions only — enforced via `order.transition_status(new_status)`:**
```
PENDING → CONFIRMED (Daraja webhook payment confirmed)
PENDING → CANCELLED (customer cancels pre-payment, or STK EXPIRED)
CONFIRMED → FULFILLED (items dispatched / dine-in order delivered)
FULFILLED → COMPLETED (customer confirms, or auto after 48h via Celery Beat)
CONFIRMED → CANCELLED (merchant cancel — must trigger M-Pesa reversal if payment confirmed)
COMPLETED / CANCELLED → terminal (no further transitions)
```
- Never set `order.status = 'x'` directly — always call `order.transition_status('x')`; invalid transitions raise `InvalidStatusTransition`
- Cancelling a `CONFIRMED` order requires M-Pesa reversal check first — never cancel a paid order without reversing
- `FULFILLED → COMPLETED` auto-transition: idempotent Celery Beat job runs hourly for orders fulfilled > 48h
- Cart cleared in Redis on `CONFIRMED` transition only — never on `PENDING`; if payment fails, cart must still be intact for retry

**Guest checkout:**
- Guest orders have `customer = None`; phone + name in `Order.guest_phone` (encrypted) + `Order.guest_name`
- Guest orders retrievable by `order_reference` + `guest_phone` only — never by email or name alone
- Guest accounts never retroactively converted to registered accounts — permanently anonymous

---

## Usage Guidelines

**For AI Agents:**
- Read this file in full before implementing any story or task
- Follow ALL rules exactly — when two rules conflict, the more restrictive one wins
- When in doubt about tenant isolation: add `TenantModel` / `TenantViewSet` — never omit them
- When in doubt about money: use `DecimalField` string format — never float
- When in doubt about async: use `transaction.on_commit` — never call `.delay()` inside a transaction
- Update this file if you discover a new unobvious pattern during implementation

**For KAFURAHA (Humans):**
- Keep rules lean and specific — remove any rule that becomes "obvious" after 3+ months of implementation
- Update technology versions when dependencies are upgraded
- Review after each sprint for new patterns that emerged during development
- Add new sections as Phase 2 (SSE, S3, analytics optimisation) and Phase 3 (AI engine) patterns emerge

_Last Updated: 2026-02-25_
