---
stepsCompleted: [step-01-init, step-02-context, step-03-starter, step-04-decisions, step-05-patterns, step-06-structure, step-07-validation, step-08-complete]
lastStep: 8
status: 'complete'
completedAt: '2026-02-24'
inputDocuments:
  - _bmad-output/planning-artifacts/product-brief-joat_stores-2026-02-23.md
  - _bmad-output/planning-artifacts/prd.md
workflowType: 'architecture'
project_name: 'joat_stores'
user_name: 'KAFURAHA'
date: '2026-02-24'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

---

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**

~47 FRs organized into 8 categories:
1. **Multi-Tenant Platform** — domain routing, store resolution, tenant lifecycle, tenant type config
2. **Retail Commerce** — product catalog (variants, inventory, media), cart (Redis), order lifecycle, guest + auth checkout
3. **F&B Operations** — restaurant: QR dine-in, modifier groups, kitchen view, table sessions, time-based menus; bar: tabs, rounds, happy hour pricing, age-restricted items
4. **Payments** — M-Pesa STK Push as primary rail (checkout, bill, tab, SaaS billing); card scaffold; Daraja webhook handling
5. **Auth & RBAC** — JWT with store-scoped claims, 4 roles (platform_admin, store_owner, store_manager, customer), feature-flag access per plan
6. **Async Infrastructure** — Celery workers (order emails, low-stock alerts, billing reminders, analytics reports, payment reconciliation), Celery Beat scheduled jobs, dead-letter queue
7. **Analytics** — per-store (revenue, orders, AOV, top products) + F&B-specific (peak hours, table turn rate) + platform (GMV, tenant health, unit economics)
8. **SaaS Scaffold** — Plan model, StoreSubscription lifecycle, usage limits (product/staff/API), feature flags, M-Pesa renewal flow

**Non-Functional Requirements:**

| NFR | Target |
|---|---|
| API response p95 | < 300ms MVP, < 150ms Month 12 |
| API uptime | 99.5% MVP, 99.9% Month 12 |
| Tenant isolation | Zero cross-tenant data incidents |
| M-Pesa STK Push success | > 98% on valid numbers |
| Celery task delivery | > 99% with DLQ + retry |
| Cart persistence | 30-day Redis TTL |
| QR menu load (3G) | < 2 seconds |
| Mobile checkout | 320px min, 3G complete |
| First page load | < 200KB total weight |
| Security | OWASP Top 10 + pen-test checklist |
| Compliance | Kenya DPA 2019, Daraja API rules, age-restriction enforcement |

**Scale & Complexity:**

- Primary domain: Full-stack (Django+DRF + Next.js + PostgreSQL + Redis + Celery + Nginx + Docker)
- Complexity level: Medium-High
- Estimated architectural components: ~15
- UX surfaces: 3 (consumer storefront, store admin, platform admin)
- Vertical modules: 2 primary (retail, F&B) with bar as F&B sub-type
- Integrations: 3 at MVP (Daraja, email provider, Google Sign-In), 4 in Phase 2

### Technical Constraints & Dependencies

1. **VPS Zero-Conflict** — Existing live services on target VPS; Docker network isolation + port pre-flight audit mandatory before any deployment
2. **Solo Developer** — Architecture must minimize operational complexity; Docker Compose single-file orchestration preferred over Kubernetes; no managed services until Phase 2
3. **Shared Database, Shared Schema** — Multi-tenancy via `store_id` FK (not separate DBs, not separate schemas); simpler ops, stricter isolation enforcement required
4. **Tenant Type Locked Post-Order** — Switching vertical after first order creates data integrity risk; schema must accommodate this constraint
5. **Daraja Sandbox First** — Production M-Pesa credentials unavailable until business registration complete; architecture must support full sandbox → production credential swap via env vars
6. **Kenya DPA 2019** — VPS must be Kenya/EAC-hosted; PII encrypted at rest; audit log on all admin PII access; 72-hour breach notification window
7. **3G Mobile-First** — Image pipeline must compress to WebP server-side; API responses paginated (cursor-based); no unbounded list endpoints

### Cross-Cutting Concerns Identified

1. **Tenant Isolation** — Enforced at 5 layers: middleware (request.store resolution), base queryset (TenantQuerySet), serializer (auto-populate store), permission class (IsStoreScoped), admin (StoreAdmin base class)
2. **Authentication & Authorization** — JWT with store_id claim; RBAC permission matrix; plan-based feature flags on every plan-limited endpoint
3. **M-Pesa Payment Flow** — STK Push → webhook confirmation → order/tab/subscription status update; retry queue; reconciliation job; reversal API
4. **Async Reliability** — Every user-facing async action (email, alert, billing) needs retry policy, DLQ, and health visibility; silent failure is a launch risk
5. **PII Compliance** — Phone/email masked in logs; encrypted at rest; soft-delete + anonymise on deletion; audit trail on admin access
6. **Mobile Performance** — WebP compression, cursor pagination, < 200KB page weight, 3G-capable checkout flow
7. **Analytics Data Capture** — Analytics events must be captured as side effects of order, payment, and inventory operations; not a bolt-on

---

## Starter Template Evaluation

### Primary Technology Domain

Full-stack multi-component architecture. The tech stack is fully prescribed in the PRD — no starter template evaluation needed at the stack selection level. Evaluation focuses on initialization approach per component.

### Stack Components & Initialization

**Backend: Django + DRF**

Recommended starter: `cookiecutter/cookiecutter-django`
- Gold-standard Django project scaffold; actively maintained
- Ships with: Docker Compose, PostgreSQL, Celery + Redis, environment management, production-grade settings split, structured logging
- Aligns with joat_stores requirements out of the box

```bash
pip install cookiecutter
cookiecutter gh:cookiecutter/cookiecutter-django
# Select: PostgreSQL, Celery, Redis, Docker, DRF, no Heroku
```

Alternative (clean start): `django-admin startproject`
```bash
django-admin startproject joat_backend .
```

Recommendation: Use `cookiecutter-django` — it eliminates ~2 weeks of boilerplate setup (Docker, Celery, settings management) that the PRD requires.

---

**Frontend — Consumer Storefront(s): Next.js**

```bash
npx create-next-app@latest storefront \
  --typescript --tailwind --eslint --app
```

One base app; per-tenant theming via domain context + CSS variables. All storefronts share the same Next.js codebase, branded at runtime.

---

**Frontend — Admin Dashboard (Store + Platform): Next.js**

```bash
npx create-next-app@latest admin \
  --typescript --tailwind --eslint --app
```

Single admin app serving both store-scoped and platform-admin views, gated by RBAC role from JWT claims.

---

### Project Repository Structure

```
joat_stores/
├── backend/          # cookiecutter-django (Django + DRF)
├── storefront/       # Next.js — consumer-facing storefronts
├── admin/            # Next.js — store admin + platform admin
├── nginx/            # Nginx configs (per-tenant domain routing)
└── docker-compose.yml
```

### Architectural Decisions Established by Starters

| Decision | Choice | Source |
|---|---|---|
| Language (backend) | Python 3.14.3 | PRD prescribed |
| Language (frontend) | TypeScript | create-next-app default |
| Framework (backend) | Django 5.2 LTS | PRD prescribed |
| Framework (frontend) | Next.js 16.x App Router | PRD prescribed |
| Styling | Tailwind CSS | create-next-app flag |
| Database | PostgreSQL 17.x | cookiecutter-django |
| Cache / Queue broker | Redis 8.6 | cookiecutter-django |
| Async worker | Celery 5.6.2 | cookiecutter-django |
| Container orchestration | Docker Compose | cookiecutter-django |
| API framework | Django REST Framework | PRD prescribed |
| Environment config | django-environ (.env) | cookiecutter-django |
| Settings split | base / local / production | cookiecutter-django |

**Note:** Project initialization (cookiecutter-django + two create-next-app calls) should be the first implementation story.

---

## Core Architectural Decisions

### Decision Priority Analysis

**Critical (block implementation):**
- Soft delete + PII anonymisation pattern
- JWT library + store_id claim strategy
- Google Sign-In integration approach
- Real-time update strategy (kitchen / order status)
- Media storage approach
- Frontend state management

**Important (shape architecture):**
- PII encryption at rest
- Analytics query approach
- Server vs Client component strategy
- Auth handling in Next.js
- Error monitoring

**Deferred (post-MVP):**
- SSE / WebSockets for real-time (upgrade from polling)
- Materialised views for analytics (upgrade from ORM aggregations)
- S3/R2 media storage (upgrade from local VPS volume)
- Full-text search (Elasticsearch / pgvector)

---

### Data Architecture

| Decision | Choice | Rationale |
|---|---|---|
| Soft delete | `django-safedelete` | Transparent queryset filtering; DPA-compliant `deleted_at` + PII anonymisation hook |
| PII encryption | `django-encrypted-fields` | Field-level, transparent to ORM, testable, per-column control |
| Analytics queries | Django ORM + annotations | Sufficient at MVP; materialised views as Phase 2 optimisation |
| Migrations | Django migrations (standard) | No alternative; standard practice |
| Complex filtering | `django-filter` + DRF SearchFilter | Standard DRF pattern; defer full-text search to Phase 2 |

---

### Authentication & Security

| Decision | Choice | Rationale |
|---|---|---|
| JWT library | `djangorestframework-simplejwt` | DRF-native; custom token serializer adds `store_id` claim |
| Google Sign-In | `django-allauth` social adapter | Handles OAuth2 PKCE, account linking, email collision edge cases |
| CORS | `django-cors-headers` | Standard; configured per-environment |
| Security middleware | Django defaults + DRF throttle | Rate limits read from `request.store.subscription.plan` |
| PII in logs | `structlog` with PII scrubber processor | Phone/email → hash in all log output |

---

### API & Communication Patterns

| Decision | Choice | Rationale |
|---|---|---|
| Real-time updates | Polling (5–10s) at MVP | Removes ASGI complexity from VPS; kitchen view latency acceptable |
| Real-time (Phase 2) | Server-Sent Events | Upgrade path from polling; HTTP-native, Nginx-compatible |
| Media storage | Local VPS volume + Nginx | Zero cost/complexity at MVP; S3/R2 migration in Phase 2 |
| File pipeline | Server-side WebP compression via `Pillow` | Enforces < 800KB, 3G performance |
| Image upload | Direct to Django API → Pillow → save | No third-party upload service at MVP |

---

### Frontend Architecture

| Decision | Choice | Rationale |
|---|---|---|
| Component default | Server Components | Minimises JS bundle; < 200KB page weight; 3G performance |
| Client Components | Interactive islands only | Cart drawer, checkout form, kitchen poll view, auth modals |
| Server state | TanStack Query (React Query) | Cart mutations, order status, checkout — caching + optimistic updates |
| UI state | Zustand | Cart open/close, modal state, theme vars — lightweight |
| Forms | `react-hook-form` + `zod` | Standard pairing; TypeScript schema shared with API types |
| Auth in Next.js | Custom JWT (memory + httpOnly cookie) | `next-auth` conflicts with `store_id` claim; axios interceptors handle refresh |
| API client | `axios` with interceptor for token refresh | Consistent base URL, auth header, error envelope parsing |

---

### Infrastructure & Deployment

| Decision | Choice | Rationale |
|---|---|---|
| Error monitoring | Sentry (free tier) | Exception tracking + async task failure visibility |
| Logging | `structlog` (backend) + `pino` (frontend) | Structured JSON logs; PII scrubber processor |
| CI/CD | GitHub Actions | Lint + test + SSH deploy on push to main; protects VPS |
| Backup | Celery Beat `pg_dump` daily → `/backups/` 7-day rotation | No external service; sufficient at MVP |
| Redis persistence | AOF enabled in Docker Compose | Prevents cart data loss on container restart |
| VPS pre-flight | Bash audit script run before `docker compose up` | Checks ports, network names, conflicting containers |
| Celery monitoring | Celery Flower (Docker service) | Queue depth + worker heartbeat; `/health/workers/` endpoint |

---

### Decision Impact Analysis

**Implementation Sequence:**
1. Django project init (cookiecutter) → tenant middleware + base model → JWT + RBAC
2. Postgres schema + migrations → Store model + TenantQuerySet
3. Celery + Redis setup → task categories + DLQ + health endpoint
4. M-Pesa Daraja integration → STK Push → webhook handler
5. Retail module → product catalog → cart → order → checkout
6. Restaurant module → menu → QR → table session → kitchen view
7. Bar module → tab → round → happy hour → tab settlement
8. Next.js storefront → per-tenant theming → TanStack Query API layer
9. Next.js admin dashboard → RBAC-gated views → analytics
10. Nginx config → per-tenant domain routing → Docker Compose full stack
11. GitHub Actions CI/CD → Sentry → monitoring baseline

**Cross-Component Dependencies:**
- Tenant middleware must exist before any business model can be created
- `TenantQuerySet` base class must be the parent of every model queryset
- JWT `store_id` claim must be established before any storefront or admin auth flow
- Celery DLQ must be configured before any async task is written (order email, alerts)
- M-Pesa Daraja sandbox credentials must be in `.env` before any payment endpoint is tested

---

## Implementation Patterns & Consistency Rules

### Critical Conflict Points Identified

12 areas where AI agents could make different choices and break the system.

---

### Naming Patterns

**Database Naming Conventions:**

| Pattern | Rule | Example |
|---|---|---|
| Table names | Django default: `{app}_{model}` snake_case plural | `store_product`, `order_orderitem` |
| Column names | snake_case always | `store_id`, `created_at`, `is_active` |
| Foreign keys | `{model}_id` suffix | `store_id`, `product_id`, `customer_id` |
| Indexes | `idx_{table}_{column(s)}` | `idx_store_product_slug` |
| Unique constraints | `uq_{table}_{column(s)}` | `uq_store_slug` |
| Many-to-many through | `{app}_{model_a}_{model_b}` | `order_order_products` |

**Anti-pattern:** Never use `userId`, `StoreID`, or mixed casing in DB columns.

---

**API Naming Conventions:**

| Pattern | Rule | Example |
|---|---|---|
| Resources | Plural noun, lowercase, hyphenated | `/api/v1/products/`, `/api/v1/order-items/` |
| Nested resources | Max 2 levels deep | `/api/v1/products/{id}/variants/` |
| Actions (non-CRUD) | POST to `/{resource}/{id}/{action}/` | `/api/v1/orders/{id}/confirm/` |
| Query parameters | snake_case | `?category_id=2&page_size=20` |
| Custom headers | `X-{Name}` capitalised | `X-Store-ID`, `X-Request-ID` |
| API version | Always `/api/v1/` prefix | Never `/v1/api/` or unversioned |

**Anti-pattern:** Never use `/api/v1/getProduct/` (RPC-style) or `/api/v1/product/` (singular).

---

**Code Naming Conventions:**

| Context | Convention | Example |
|---|---|---|
| Django models | PascalCase singular | `Product`, `OrderItem`, `StoreSubscription` |
| Django apps | snake_case singular domain | `store`, `product`, `order`, `payment`, `restaurant`, `bar` |
| Python functions/methods | snake_case verbs | `get_active_products()`, `send_confirmation()` |
| Python variables | snake_case | `store_id`, `order_total`, `is_active` |
| Django views/serializers | `{Model}{Action}View/Serializer` | `ProductListView`, `OrderCreateSerializer` |
| Celery tasks | `{verb}_{noun}` in `tasks.py` | `send_order_confirmation`, `trigger_low_stock_alert` |
| React components | PascalCase | `ProductCard`, `CartDrawer`, `KitchenOrderList` |
| React files | PascalCase `.tsx` | `ProductCard.tsx`, `CartDrawer.tsx` |
| Next.js route files | lowercase `page.tsx`, `layout.tsx` | App Router convention |
| TypeScript interfaces | PascalCase `I` prefix | `IProduct`, `IOrder`, `ICartItem` |
| TypeScript types | PascalCase | `ProductVariant`, `OrderStatus` |
| Zustand stores | camelCase `use{Domain}Store` | `useCartStore`, `useAuthStore` |
| TanStack Query keys | array with domain prefix | `['products', storeId]`, `['order', orderId]` |
| Environment variables | SCREAMING_SNAKE_CASE | `DJANGO_SECRET_KEY`, `MPESA_CONSUMER_KEY` |

---

### Structure Patterns

**Django Backend Organisation:**

```
backend/
├── apps/
│   ├── store/          # Tenant model, middleware, RBAC
│   ├── product/        # Product catalog, variants, inventory
│   ├── order/          # Order lifecycle, cart
│   ├── payment/        # M-Pesa, payment records
│   ├── restaurant/     # Menu, QR, table, kitchen
│   ├── bar/            # Tab, rounds, happy hour
│   ├── analytics/      # Aggregation models, dashboard views
│   ├── notifications/  # Celery tasks: email, alerts
│   └── saas/           # Plan, StoreSubscription
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── local.py
│   │   └── production.py
│   ├── urls.py
│   └── celery.py
└── core/
    ├── models.py       # TenantModel, SoftDeleteModel base classes
    ├── querysets.py    # TenantQuerySet base class
    ├── permissions.py  # IsStoreScoped, IsPlatformAdmin base classes
    ├── serializers.py  # TenantSerializer base class
    ├── views.py        # TenantViewSet base class
    └── exceptions.py   # Custom exception handler
```

Each app MUST contain: `models.py`, `serializers.py`, `views.py`, `urls.py`, `tasks.py` (if async), `permissions.py` (if needed), `tests/` directory with `test_models.py`, `test_views.py`, `test_tasks.py`.

---

**Next.js Frontend Organisation:**

```
storefront/
├── app/
│   ├── [domain]/          # Per-tenant dynamic segment
│   │   ├── page.tsx
│   │   ├── products/
│   │   ├── cart/
│   │   └── checkout/
│   └── layout.tsx
├── components/
│   ├── product/           # ProductCard, ProductGrid, VariantSelector
│   ├── cart/              # CartDrawer, CartItem, CartSummary
│   ├── checkout/          # CheckoutForm, PaymentStep, MpesaPrompt
│   ├── restaurant/        # MenuSection, ModifierModal, TableOrderSummary
│   └── ui/                # Button, Input, Modal — shared primitives
├── lib/
│   ├── api.ts             # axios instance + interceptors
│   ├── auth.ts            # JWT token management
│   └── utils.ts           # formatCurrency, formatDate, etc.
├── stores/
│   ├── cartStore.ts
│   └── authStore.ts
└── types/
    └── index.ts           # Shared TypeScript interfaces
```

---

### Format Patterns

**API Response Formats:**

Single object success:
```json
{ "data": { "id": 1, "name": "iPhone Charger", "price": "1500.00", "store_id": 3 } }
```

List success (cursor pagination):
```json
{ "data": [...], "meta": { "count": 142, "next": "cD0yMDI2...", "previous": null } }
```

Validation error (422):
```json
{ "errors": [{ "field": "phone", "message": "Must be a valid Kenyan phone number.", "code": "INVALID_PHONE" }] }
```

Non-field error (400/403/404):
```json
{ "errors": [{ "field": null, "message": "Store not found.", "code": "STORE_NOT_FOUND" }] }
```

**Anti-pattern:** Never return `{"error": "something went wrong"}`. Never return HTTP 200 with error content.

---

**Data Formats:**

| Data Type | Format | Example |
|---|---|---|
| Money | String, 2 decimal places | `"1500.00"` (KES) |
| Phone (M-Pesa) | E.164 | `"+254712345678"` |
| Datetime | ISO 8601 UTC | `"2026-02-24T12:00:00Z"` |
| Date only | ISO 8601 | `"2026-02-24"` |
| Boolean | JSON native | `true`/`false` — never `1`/`0` |
| Null | Always included | `null` — never omit optional absent fields |
| IDs | Integer (DB PK) | `1`, `42` — never UUID at MVP |
| Tenant type | Lowercase enum | `"retail"`, `"restaurant"`, `"bar"` |
| Order status | Lowercase enum | `"pending"`, `"confirmed"`, `"fulfilled"`, `"completed"`, `"cancelled"` |

**Anti-pattern:** Never use floats for money. Never use Unix timestamps in API responses.

---

### Communication Patterns

**Celery Task Template (all tasks must follow):**

```python
@shared_task(bind=True, max_retries=5, default_retry_delay=60, queue='order.notifications')
def send_order_confirmation(self, order_id: int) -> None:
    try:
        order = Order.objects.get(id=order_id)
        # ... send email
    except Order.DoesNotExist:
        return  # Do not retry — order was deleted
    except EmailProviderError as exc:
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

Queue assignment: `order.notifications`, `inventory.alerts`, `billing.reminders`, `payments.reconciliation`, `analytics.reports`

**M-Pesa Phone Normalisation — always use canonical function:**

```python
# core/utils.py — single source of truth
def normalise_mpesa_phone(raw: str) -> str:
    """Converts any Kenyan phone format to E.164 +254XXXXXXXXX"""
    digits = re.sub(r'\D', '', raw)
    if digits.startswith('0') and len(digits) == 10:
        return f'+254{digits[1:]}'
    if digits.startswith('254') and len(digits) == 12:
        return f'+{digits}'
    raise ValueError(f'Cannot normalise phone: {raw}')
```

**Anti-pattern:** Never normalise phone numbers inline in a view or serializer.

---

### Process Patterns

**Tenant Isolation — Non-Negotiable:**

```python
# CORRECT
class Product(TenantModel):
    name = models.CharField(max_length=255)

# WRONG — missing TenantModel
class Product(models.Model):
    store = models.ForeignKey(Store, ...)  # queryset not enforced
```

```python
# CORRECT
class ProductViewSet(TenantViewSet):
    serializer_class = ProductSerializer
    queryset = Product.objects.all()

# WRONG — direct queryset leaks cross-tenant data
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
```

**Frontend Error Handling:**

```typescript
// CORRECT — TanStack Query handles error state
const { mutate } = useMutation({
  mutationFn: placeOrder,
  onError: (err) => toast.error(err.errors[0].message)
})

// WRONG — unhandled promise rejection
fetch('/api/v1/orders/').then(res => res.json())
```

**Frontend Loading States — always use TanStack Query states, never manual `isLoading`:**

```typescript
const { data, isLoading, isError } = useQuery({ queryKey: ['products', storeId], queryFn: fetchProducts })
if (isLoading) return <ProductGridSkeleton />
if (isError) return <ErrorState />
```

---

### Enforcement Guidelines

**All AI Agents MUST:**

1. Inherit every tenant model from `TenantModel` — never `models.Model` directly
2. Inherit every tenant viewset from `TenantViewSet` — never `viewsets.ModelViewSet` directly
3. Use the `{data, meta, errors}` API envelope — never bare objects or custom shapes
4. Store all money as `DecimalField(max_digits=10, decimal_places=2)` — never `FloatField`
5. Use `normalise_mpesa_phone()` from `core/utils.py` — never inline phone normalisation
6. Place Celery tasks in `apps/{domain}/tasks.py` — never define tasks in views
7. Use ISO 8601 UTC for all datetimes in DB and API responses
8. Use `structlog` for all backend logging — never `print()` or bare `logging.info()`
9. Never commit secrets — all credentials via environment variables via `django-environ`
10. Include `store_id` scope in every integration test that touches tenant data

**CI Enforcement:**
- `pytest -k "cross_tenant"` — any cross-tenant data leak fails the build
- `flake8` + `black` + `isort` enforced pre-merge
- TypeScript strict mode — no `any` types without explicit justification comment

---

## Project Structure & Boundaries

### Complete Project Directory Structure

```
joat_stores/                          # Monorepo root
├── .github/
│   └── workflows/
│       ├── ci.yml                    # Lint + test on PR
│       └── deploy.yml               # SSH deploy on merge to main
├── backend/                          # Django + DRF
├── storefront/                       # Next.js — consumer storefronts
├── admin/                            # Next.js — store admin + platform admin
├── nginx/                            # Nginx reverse proxy configs
├── scripts/
│   ├── preflight.sh                  # VPS pre-flight audit (ports, networks, conflicts)
│   ├── backup.sh                     # pg_dump + Redis snapshot
│   └── deploy.sh                     # Pull + docker compose up -d
├── docker-compose.yml                # Full stack (dev + prod base)
├── docker-compose.prod.yml           # Production overrides
├── .env.example
└── README.md
```

**Backend:**

```
backend/
├── Dockerfile
├── manage.py
├── requirements/
│   ├── base.txt                      # Django, DRF, psycopg2, redis, celery, etc.
│   ├── local.txt                     # pytest, factory-boy, debug-toolbar
│   └── production.txt                # gunicorn, sentry-sdk
├── .env.example
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── local.py
│   │   └── production.py
│   ├── urls.py                       # Root URL conf — mounts /api/v1/ + health
│   ├── wsgi.py
│   └── celery.py                     # Celery app + beat schedule
├── core/
│   ├── models.py                     # TenantModel, SoftDeleteModel base classes
│   ├── querysets.py                  # TenantQuerySet
│   ├── permissions.py                # IsStoreScoped, IsPlatformAdmin, IsStoreOwner, IsStoreManager
│   ├── serializers.py                # TenantSerializer (auto-injects store from request)
│   ├── views.py                      # TenantViewSet (scopes all queries to request.store)
│   ├── middleware.py                 # TenantMiddleware — resolves request.store from domain / X-Store-ID
│   ├── exceptions.py                 # custom_exception_handler → {errors:[{field,message,code}]}
│   ├── pagination.py                 # StoreCursorPagination
│   └── utils.py                      # normalise_mpesa_phone, format_currency, mask_pii
└── apps/
    ├── store/                        # Tenant model + lifecycle
    │   ├── models.py                 # Store, StoreSettings, StoreTheme
    │   ├── serializers.py
    │   ├── views.py
    │   ├── urls.py
    │   ├── admin.py
    │   └── tests/
    │       ├── test_models.py
    │       ├── test_views.py
    │       └── test_middleware.py    # ⚠️ Cross-tenant isolation test suite
    ├── users/                        # Auth + RBAC
    │   ├── models.py                 # CustomUser, CustomerProfile
    │   ├── serializers.py
    │   ├── views.py                  # Login, register, token refresh, Google OAuth callback
    │   ├── urls.py
    │   └── tests/
    │       ├── test_auth.py
    │       └── test_permissions.py
    ├── product/                      # Retail: catalog
    │   ├── models.py                 # Category, Product, ProductVariant, ProductImage, Inventory
    │   ├── serializers.py
    │   ├── views.py
    │   ├── urls.py
    │   ├── filters.py                # ProductFilter (price range, category, in_stock)
    │   └── tests/
    ├── order/                        # Retail: cart + order lifecycle
    │   ├── models.py                 # Cart, CartItem, Order, OrderItem, ShippingAddress
    │   ├── serializers.py
    │   ├── views.py
    │   ├── urls.py
    │   ├── services.py               # create_order_from_cart(), calculate_totals()
    │   └── tests/
    │       ├── test_cart.py
    │       ├── test_order.py
    │       └── test_checkout.py
    ├── payment/                      # M-Pesa + payment records
    │   ├── models.py                 # Payment, MpesaTransaction, PaymentWebhookLog
    │   ├── serializers.py
    │   ├── views.py                  # /initiate-stk/, /mpesa-callback/
    │   ├── urls.py
    │   ├── daraja.py                 # Daraja API client (STK Push, OAuth2, callback verification)
    │   └── tests/
    │       ├── test_daraja.py
    │       └── test_webhook.py
    ├── inventory/                    # Stock management + supplier alerts
    │   ├── models.py                 # InventoryEvent, SupplierContact, LowStockAlert
    │   ├── serializers.py
    │   ├── views.py
    │   ├── urls.py
    │   ├── tasks.py                  # trigger_low_stock_alert, send_supplier_email
    │   └── tests/
    ├── restaurant/                   # F&B: restaurant module
    │   ├── models.py                 # Menu, MenuSection, MenuItem, ModifierGroup, Modifier
    │   │                             # Table, TableSession, DineInOrder, KitchenTicket
    │   ├── serializers.py
    │   ├── views.py                  # Menu, table session, kitchen order list
    │   ├── urls.py
    │   ├── qr.py                     # QR code generation (encodes store + table ID)
    │   └── tests/
    │       ├── test_menu.py
    │       ├── test_table_session.py
    │       └── test_kitchen_view.py
    ├── bar/                          # F&B: bar sub-type
    │   ├── models.py                 # Tab, TabRound, HappyHourRule, AgeRestrictionLog
    │   ├── serializers.py
    │   ├── views.py                  # Tab open/close, round add, happy hour status
    │   ├── urls.py
    │   └── tests/
    │       ├── test_tab.py
    │       └── test_happy_hour.py
    ├── analytics/                    # Dashboard data
    │   ├── models.py                 # DailyRevenueSummary, TopProduct, TenantHealthSnapshot
    │   ├── serializers.py
    │   ├── views.py                  # Store analytics, platform analytics, unit economics
    │   ├── urls.py
    │   ├── tasks.py                  # generate_daily_summary (Beat), send_merchant_digest
    │   └── tests/
    ├── notifications/                # Async email
    │   ├── tasks.py                  # send_order_confirmation, send_low_stock_alert, send_renewal_reminder
    │   ├── templates/
    │   │   ├── order_confirmation.html
    │   │   ├── low_stock_alert.html
    │   │   └── subscription_renewal.html
    │   └── tests/
    └── saas/                         # SaaS subscription scaffold
        ├── models.py                 # Plan, StoreSubscription
        ├── serializers.py
        ├── views.py
        ├── urls.py
        ├── tasks.py                  # send_renewal_reminder, process_mpesa_subscription_renewal
        └── tests/
```

**Storefront (Next.js):**

```
storefront/
├── Dockerfile
├── package.json
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── .env.local.example
├── middleware.ts                     # Resolves tenant from hostname → sets context
├── app/
│   ├── layout.tsx                    # Root: TenantThemeProvider
│   ├── globals.css
│   ├── (store)/
│   │   ├── page.tsx                  # Homepage
│   │   ├── products/
│   │   │   ├── page.tsx
│   │   │   └── [slug]/page.tsx
│   │   ├── cart/page.tsx
│   │   ├── checkout/page.tsx
│   │   ├── orders/
│   │   │   ├── page.tsx
│   │   │   └── [id]/page.tsx
│   │   └── auth/
│   │       ├── login/page.tsx
│   │       └── register/page.tsx
│   └── (restaurant)/
│       └── table/[tableId]/page.tsx  # QR dine-in entry point
├── components/
│   ├── ui/                           # Button, Input, Modal, Toast, Skeleton
│   ├── layout/
│   │   ├── Header.tsx
│   │   ├── Footer.tsx
│   │   └── TenantThemeProvider.tsx
│   ├── product/
│   │   ├── ProductCard.tsx
│   │   ├── ProductGrid.tsx
│   │   ├── ProductDetail.tsx
│   │   ├── VariantSelector.tsx       # Client Component
│   │   └── SizeGuideModal.tsx        # Client Component
│   ├── cart/
│   │   ├── CartDrawer.tsx            # Client Component
│   │   ├── CartItem.tsx
│   │   └── CartSummary.tsx
│   ├── checkout/
│   │   ├── CheckoutForm.tsx
│   │   ├── MpesaPrompt.tsx           # Polls STK Push status
│   │   └── OrderConfirmation.tsx
│   └── restaurant/
│       ├── MenuSection.tsx
│       ├── MenuItemCard.tsx
│       ├── ModifierModal.tsx         # Client Component
│       ├── TableOrderSummary.tsx
│       └── BillSplitModal.tsx        # Client Component
├── lib/
│   ├── api.ts                        # axios + auth interceptor
│   ├── auth.ts                       # JWT: memory + httpOnly cookie refresh
│   ├── tenant.ts
│   └── utils.ts                      # formatCurrency, formatDate (Africa/Nairobi)
├── stores/
│   ├── cartStore.ts                  # Zustand
│   └── authStore.ts                  # Zustand
├── hooks/
│   ├── useProducts.ts
│   ├── useCart.ts
│   ├── useOrder.ts
│   ├── useTableSession.ts
│   └── useMpesaStatus.ts
└── types/index.ts
```

**Admin (Next.js):**

```
admin/
├── Dockerfile
├── package.json
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── .env.local.example
├── middleware.ts                     # Auth guard + role check
├── app/
│   ├── layout.tsx
│   ├── globals.css
│   ├── login/page.tsx
│   ├── (store-admin)/
│   │   ├── layout.tsx               # Sidebar + Topbar
│   │   ├── dashboard/page.tsx
│   │   ├── products/
│   │   │   ├── page.tsx
│   │   │   ├── new/page.tsx
│   │   │   └── [id]/page.tsx
│   │   ├── orders/
│   │   │   ├── page.tsx
│   │   │   └── [id]/page.tsx
│   │   ├── inventory/page.tsx
│   │   ├── analytics/page.tsx
│   │   ├── menu/
│   │   │   ├── page.tsx
│   │   │   └── [id]/page.tsx
│   │   ├── kitchen/page.tsx         # Polls every 5s
│   │   └── settings/page.tsx
│   └── (platform-admin)/
│       ├── layout.tsx
│       ├── dashboard/page.tsx
│       ├── tenants/
│       │   ├── page.tsx
│       │   ├── new/page.tsx
│       │   └── [id]/page.tsx
│       └── analytics/page.tsx        # Unit economics
├── components/
│   ├── ui/
│   ├── layout/
│   │   ├── Sidebar.tsx
│   │   ├── Topbar.tsx
│   │   └── RoleGuard.tsx
│   ├── product/
│   │   ├── ProductForm.tsx
│   │   ├── ProductTable.tsx
│   │   └── VariantManager.tsx
│   ├── order/
│   │   ├── OrderTable.tsx
│   │   └── OrderStatusBadge.tsx
│   ├── analytics/
│   │   ├── RevenueChart.tsx
│   │   ├── TopProductsTable.tsx
│   │   └── TenantHealthCard.tsx
│   ├── kitchen/
│   │   └── KitchenOrderList.tsx     # Client Component; refetchInterval: 5000
│   └── platform/
│       ├── TenantTable.tsx
│       ├── TenantForm.tsx
│       └── UnitEconomicsCard.tsx
├── lib/
│   ├── api.ts
│   ├── auth.ts
│   └── utils.ts
├── stores/authStore.ts
├── hooks/
│   ├── useOrders.ts
│   ├── useAnalytics.ts
│   └── useKitchenOrders.ts          # refetchInterval: 5000
└── types/index.ts
```

**Infrastructure:**

```
nginx/
├── nginx.conf
└── conf.d/
    ├── api.conf                      # Proxy /api/ → backend:8000
    ├── storefront.conf               # Default catch-all → storefront:3000
    ├── admin.conf                    # admin.joat.com → admin:3001
    └── tenants/
        ├── techstore.joat.com.conf
        └── fashionstore.joat.com.conf

scripts/
├── preflight.sh                      # Checks ports 80/443/5432/6379, no container conflicts
├── backup.sh                         # pg_dump → /backups/$(date).sql.gz; 7-day rotation
└── deploy.sh                         # git pull → docker compose pull → up -d
```

---

### Architectural Boundaries

**API Boundaries:**

| Boundary | Contract |
|---|---|
| Storefront → Django | REST `/api/v1/` via axios; JWT Bearer; `{data,meta,errors}` envelope |
| Admin → Django | Same REST; `platform_admin` token gets broader queryset scope |
| Nginx → Django | Proxy to `backend:8000`; passes `X-Forwarded-Host` for tenant resolution |
| Django → Daraja | HTTPS outbound; OAuth2; callback on `/api/v1/payments/mpesa-callback/` |
| Django → Email | Celery async → SendGrid/SES SMTP API |
| Django → Redis | Celery broker + cart cache + JWT blacklist + rate limit counters |

**Data Flow — Retail Checkout:**

```
Customer → Nginx → Storefront → POST /api/v1/orders/checkout/
  → Order created (Postgres)
  → POST to Daraja STK Push
    → Customer approves PIN
    → Daraja POSTs to /api/v1/payments/mpesa-callback/
      → Order status → confirmed
      → Celery: send_order_confirmation.delay(order_id) → Email
```

**Data Flow — Kitchen View:**

```
Admin /kitchen/ → useKitchenOrders (5s poll)
  → GET /api/v1/restaurant/kitchen/orders/?status=pending
    → TenantViewSet filters by request.store → returns active tickets
```

---

### Requirements to Structure Mapping

| FR Category | Backend | Frontend |
|---|---|---|
| Multi-tenant routing | `core/middleware.py`, `apps/store/` | `storefront/middleware.ts`, `admin/middleware.ts` |
| Auth + RBAC | `apps/users/`, `core/permissions.py` | `lib/auth.ts`, `stores/authStore.ts` |
| Product catalog | `apps/product/` | `components/product/`, `admin/components/product/` |
| Cart | `apps/order/` (Cart model) | `stores/cartStore.ts`, `components/cart/` |
| Order lifecycle | `apps/order/` | `app/(store)/orders/`, `admin/(store-admin)/orders/` |
| M-Pesa payments | `apps/payment/daraja.py` | `components/checkout/MpesaPrompt.tsx` |
| Inventory + alerts | `apps/inventory/` | `admin/(store-admin)/inventory/` |
| Restaurant module | `apps/restaurant/` | `app/(restaurant)/`, `admin/(store-admin)/kitchen/` |
| Bar module | `apps/bar/` | Extends restaurant routes |
| Analytics | `apps/analytics/` | `admin/(store-admin)/analytics/`, `admin/(platform-admin)/analytics/` |
| SaaS scaffold | `apps/saas/` | `admin/(store-admin)/settings/` |
| Async jobs | `apps/notifications/tasks.py`, `apps/*/tasks.py` | — |
| Platform admin | `apps/store/` (admin endpoints) | `admin/(platform-admin)/` |

---

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:** All technology choices verified compatible. One known integration complexity: `django-allauth` + `djangorestframework-simplejwt` require a custom adapter — allauth creates the Django user; a custom `SocialAccountAdapter` then calls simplejwt to issue a JWT with `store_id` claim. Must be specified as an explicit sub-task in the Google Sign-In story.

**Pattern Consistency:** 3-layer tenant isolation (TenantModel → TenantViewSet → IsStoreScoped) is uniform across all 9 domain apps. Single API response envelope enforced with no exceptions. snake_case/TypeScript strict enforced by CI.

**Structure Alignment:** `core/` cleanly owns cross-cutting concerns. App Router route groups correctly isolate storefront surfaces. Admin route groups are RBAC-gated at middleware.

---

### Requirements Coverage ✅

All 8 FR categories architecturally covered. All 11 NFRs have explicit architectural support. See Requirements to Structure Mapping above for full traceability.

**Clarification — Bar/Restaurant module activation:**
- `tenant_type = 'restaurant'` → activates `apps/restaurant/` endpoints only
- `tenant_type = 'bar'` → activates `apps/restaurant/` + `apps/bar/` endpoints
- Middleware checks: `request.store.tenant_type in ['restaurant', 'bar']` for F&B gate
- Bar-specific routes additionally gated: `request.store.tenant_type == 'bar'`

---

### Gap Analysis Results

**Important (address in story specifications):**
- `docker-compose.yml` service definitions (names, ports, networks, volumes) — story #1
- Complete `.env.example` variable list — story #1
- AI scaffold stub: `apps/ai/` with placeholder files (`models.py`, `services.py` with `# TODO: Phase 3`) — SaaS epic story

**Minor (Phase 2):**
- Nginx tenant config auto-generation script
- Celery Beat cron expressions (exact timing)
- QR code URL format + security token specification

---

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed (Medium-High confirmed)
- [x] Technical constraints identified (VPS, solo dev, DPA 2019, 3G mobile)
- [x] Cross-cutting concerns mapped (7 concerns, all addressed)

**✅ Architectural Decisions**
- [x] Critical decisions documented with versions
- [x] Technology stack fully specified (15 components)
- [x] Integration patterns defined (Daraja, email, Google OAuth, Redis, Celery)
- [x] Performance considerations addressed (caching, pagination, WebP, Server Components)

**✅ Implementation Patterns**
- [x] Naming conventions established (DB, API, code — all contexts)
- [x] Structure patterns defined (backend apps, Next.js App Router)
- [x] Communication patterns specified (Celery task template, phone normalisation)
- [x] Process patterns documented (tenant isolation, error handling, loading states)
- [x] 10 mandatory enforcement rules with CI hooks

**✅ Project Structure**
- [x] Complete directory structure defined (80+ files named)
- [x] Component boundaries established
- [x] Integration points and data flows mapped
- [x] All 13 FR categories mapped to exact file locations

---

### Architecture Readiness Assessment

**Overall Status: READY FOR IMPLEMENTATION**

**Confidence Level: High**

**Key Strengths:**
- Tenant isolation enforced at 5 independent layers — extremely difficult to accidentally bypass
- M-Pesa integration treated as first-class infrastructure, not a plugin
- Server Components-first Next.js strategy directly addresses 3G performance NFR
- Celery reliability built in from day one (DLQ, retry, health endpoint)
- CI enforcement rules turn architectural intent into automated verification

**Areas for Future Enhancement:**
- Real-time kitchen updates (polling → SSE in Phase 2)
- Media storage (local VPS → S3/Cloudflare R2 in Phase 2)
- Analytics queries (ORM annotations → materialised views in Phase 2)
- AI engine (placeholder → collaborative filtering in Phase 3)

---

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all architectural decisions exactly as documented
- Every new model inherits `TenantModel` — no exceptions
- Every new viewset inherits `TenantViewSet` — no exceptions
- All money as `DecimalField(max_digits=10, decimal_places=2)` — no exceptions
- Run `pytest -k cross_tenant` locally before opening any PR touching models or views
- Refer to Implementation Patterns section for any naming or format question

**First Implementation Priority:**

```bash
# 1. Backend scaffold
pip install cookiecutter
cookiecutter gh:cookiecutter/cookiecutter-django

# 2. Frontend scaffolds
npx create-next-app@latest storefront --typescript --tailwind --eslint --app
npx create-next-app@latest admin --typescript --tailwind --eslint --app

# 3. Immediately implement core/ before any app
# core/models.py → core/querysets.py → core/middleware.py → core/permissions.py
# This foundational layer must exist before any domain app is created
```
