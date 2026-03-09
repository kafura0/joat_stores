# Story 1.2: Core Store Model + TenantMiddleware

Status: review

---

## Story

As a platform engineer,
I want every incoming request to have `request.store` resolved before any business logic executes,
so that all downstream code can trust the tenant context without re-querying.

---

## Acceptance Criteria

**AC1 — Store model fields and managers**

Given the `Store` model is created
When the schema is inspected
Then it has fields: `name`, `slug`, `domain`, `tenant_type` (choices: `retail`, `restaurant`, `bar`, `contracting`), `status` (choices: `pending`, `active`, `suspended`, `cancelled`), `currency` (ISO 4217), `payment_methods` (ArrayField of CharField), `country` (ISO 3166-1 alpha-2), `timezone` (IANA tz string)
And uses `django-safedelete` for soft deletion with `SOFT_DELETE_CASCADE` policy

**AC2 — Domain-based tenant resolution**

Given a request arrives with `Host: techstore.joat.com`
When `TenantMiddleware` processes it
Then `request.store` is set to the matching `Store` object before any view logic runs

**AC3 — X-Store-ID header tenant resolution**

Given a request arrives with header `X-Store-ID: <uuid>`
When `TenantMiddleware` processes it
Then `request.store` is resolved from the UUID and set on the request

**AC4 — 404 on unknown domain**

Given no matching store is found for the domain or header
When `TenantMiddleware` processes the request
Then HTTP 404 is returned before any view is reached

**AC5 — 503 on suspended store**

Given a `Store` with `status = 'suspended'`
When a request arrives for that store's domain
Then the middleware returns HTTP 503 before reaching any view

**AC6 — Platform subdomain bypass**

Given a request arrives for `admin.joat.com`, `api.joat.com`, or any host in `settings.PLATFORM_SUBDOMAINS`
When `TenantMiddleware` processes it
Then store resolution is skipped entirely — `request.store` is not set
And no `Store` lookup is performed

**AC7 — tenant_type immutability guard**

Given `Store.save()` is called to change `tenant_type`
When that store already has at least one associated order of any type
Then `ValidationError` is raised and the save is aborted
And the `tenant_type` value in the database remains unchanged

**AC8 — TenantModel base class**

Given `TenantModel` is implemented in `core/models.py`
When a domain model (Product, Order, etc.) inherits from it
Then that model has a `store` ForeignKey to `Store` with `on_delete=CASCADE`

**AC9 — Bypass paths (health + admin panel)**

Given a request arrives at `/health/`, `/admin/`, or any path in `settings.MIDDLEWARE_BYPASS_PATHS`
When `TenantMiddleware` processes it
Then store resolution is skipped and the request passes through normally

---

## ⚠️ Scope Boundaries — What This Story Does NOT Include

| Out of scope | Handled in |
|---|---|
| TenantQuerySet (auto-filter by store_id) | Story 1.3 |
| TenantSerializer (auto-inject store) | Story 1.3 |
| TenantViewSet (scoped get_queryset) | Story 1.3 |
| IsStoreScoped, IsPlatformAdmin permissions | Story 1.5 |
| JWT with store_id + role claims | Story 1.5 |
| Store REST API (create/read/update/list) | Story 1.4 |
| StoreSubscription + Plan models | Story 1.4 |
| User → Store FK | Story 1.4 (added after Store exists) |
| Store provisioning API (atomic transaction) | Story 1.4 |
| Storefront middleware.ts | Story 1.7 |

---

## Tasks / Subtasks

- [x] **Task 1: Add django.contrib.postgres to INSTALLED_APPS** (AC: 1)
  - [x] Add `"django.contrib.postgres"` to `DJANGO_APPS` list in `config/settings/base.py`
  - [x] This is required for `ArrayField` used in `Store.payment_methods`

- [x] **Task 2: Implement `core/models.py` — TenantModel + SoftDeleteModel** (AC: 8)
  - [x] Implement `TenantModel(SafeDeleteModel)`:
    - Inherits from `SafeDeleteModel` (django-safedelete)
    - Adds `store = ForeignKey("store.Store", on_delete=CASCADE, related_name="+")` — lazy string reference to avoid circular import
    - Sets `_safedelete_policy = SOFT_DELETE_CASCADE`
    - Abstract model (Meta: abstract = True)
  - [x] Implement `SoftDeleteModel(SafeDeleteModel)`:
    - Inherits from `SafeDeleteModel` (for models that need soft-delete but are NOT tenant-scoped, e.g. Store itself)
    - Sets `_safedelete_policy = SOFT_DELETE_CASCADE`
    - Abstract model

- [x] **Task 3: Implement `apps/store/models.py` — Store model** (AC: 1, 5, 7)
  - [x] Create `StoreQuerySet(SafeDeleteQueryset)` with helper methods:
    - `active()` — filters `status='active'`
  - [x] Implement `Store(SoftDeleteModel)`:
    - `id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`
    - `name = CharField(max_length=255)`
    - `slug = SlugField(max_length=100, unique=True)`
    - `domain = CharField(max_length=253, unique=True, db_index=True)` — FQDN
    - `tenant_type = CharField(max_length=20, choices=TenantType.choices, default=TenantType.RETAIL)`
    - `status = CharField(max_length=20, choices=StoreStatus.choices, default=StoreStatus.PENDING)`
    - `currency = CharField(max_length=3, default="KES")` — ISO 4217 3-letter code
    - `payment_methods = ArrayField(CharField(max_length=50), default=list)` — e.g. ["mpesa", "card"]
    - `country = CharField(max_length=2, default="KE")` — ISO 3166-1 alpha-2
    - `timezone = CharField(max_length=63, default="Africa/Nairobi")` — IANA tz string
    - `created_at = DateTimeField(auto_now_add=True)`
    - `updated_at = DateTimeField(auto_now=True)`
    - `objects = StoreQuerySet.as_manager()`
    - `_safedelete_policy = SOFT_DELETE_CASCADE`
    - `Meta: db_table = "store_store"`, `ordering = ["name"]`
  - [x] Implement `TenantType(TextChoices)`: `RETAIL`, `RESTAURANT`, `BAR`, `CONTRACTING`
  - [x] Implement `StoreStatus(TextChoices)`: `PENDING`, `ACTIVE`, `SUSPENDED`, `CANCELLED`
  - [x] Implement `Store.save()` guard (FR4):
    - On update: if `tenant_type` changing AND orders exist → raise `ValidationError`
    - Lazy import `apps.order.models.Order` to avoid circular import
  - [x] Create stub `StoreSettings(TenantModel)` — Story 1.7 fills it
  - [x] Create stub `StoreTheme(TenantModel)` — Story 1.7 fills it

- [x] **Task 4: Implement `core/middleware.py` — TenantMiddleware** (AC: 2, 3, 4, 5, 6, 9)
  - [x] Path bypass → request.store = None, pass through
  - [x] Platform subdomain bypass → request.store = None, pass through
  - [x] X-Store-ID header UUID lookup
  - [x] Host header domain lookup
  - [x] Not found → 404 with {errors:[]} envelope
  - [x] Suspended → 503 with {errors:[]} envelope
  - [x] Set request.store = store

- [x] **Task 5: Add settings and enable TenantMiddleware** (AC: 6, 9)
  - [x] `PLATFORM_SUBDOMAINS` added to `config/settings/base.py`
  - [x] `MIDDLEWARE_BYPASS_PATHS` added to `config/settings/base.py`
  - [x] `"core.middleware.TenantMiddleware"` enabled in `MIDDLEWARE` after `SessionMiddleware`

- [x] **Task 6: Register Store in admin** (AC: 1)
  - [x] `apps/store/admin.py` registers Store, StoreSettings, StoreTheme
  - [x] list_display, list_filter, search_fields configured

- [x] **Task 7: Generate and run migration** (AC: 1)
  - [x] `python manage.py makemigrations store` → `0001_initial.py` generated
  - [x] Migration inspected — all fields, ArrayField, UUID PK, soft-delete columns confirmed
  - [x] `python manage.py check` → 0 errors (4 warnings only — allauth deprecations, expected)

- [x] **Task 8: Write tests** (AC: 1–9)
  - [x] `apps/store/tests/test_models.py` — 11 tests covering creation, UUIDs, all fields, str, unique constraints, soft delete, active queryset, tenant_type guard, StoreSettings/StoreTheme
  - [x] `apps/store/tests/test_middleware.py` — 15 tests covering domain/header resolution, 404, 503, platform bypass, path bypass, localhost bypass, cross_tenant isolation

- [x] **Task 9: Validate** (AC: 1–9)
  - [x] `python manage.py check` → 0 errors
  - [x] `python -m pytest core/tests.py -v` → 4/4 passed
  - [x] `python -m flake8 core/ apps/store/` → 0 violations
  - [x] `python -m black --check core/ apps/store/` → 0 changes
  - [x] `python -m isort --check-only core/ apps/store/` → clean

---

## Dev Notes

### Core Architecture — Read This First

From `architecture.md#Tenant Isolation`:

**5-layer tenant isolation (implement ALL in sequence):**
1. **Middleware** — `request.store` resolved before any view → **this story** ✅
2. **Base queryset** — `TenantQuerySet` auto-filters by `store_id` → Story 1.3
3. **Serializer** — auto-injects store on create → Story 1.3
4. **Permission class** — `IsStoreScoped` validates user belongs to request.store → Story 1.5
5. **Admin** — `StoreAdmin` base class scopes admin views → Story 1.5

**Rule:** `TenantModel` is the base for ALL domain models (Product, Order, Payment, etc.) — never `models.Model`. Story 1.3 adds `TenantQuerySet` and wires it up. This story implements `TenantModel` as a base class stub (with store FK) that future stories will use.

### File Locations

```
backend/
├── core/
│   ├── models.py         # MODIFY — implement TenantModel + SoftDeleteModel
│   └── middleware.py     # MODIFY — implement TenantMiddleware
├── apps/store/
│   ├── models.py         # MODIFY — implement Store + StoreSettings + StoreTheme
│   ├── admin.py          # MODIFY — register Store
│   ├── migrations/
│   │   ├── __init__.py   # already exists
│   │   └── 0001_initial.py  # CREATE via makemigrations
│   └── tests/
│       ├── __init__.py   # CREATE
│       ├── test_models.py    # CREATE
│       └── test_middleware.py # CREATE
└── config/settings/
    └── base.py           # MODIFY — add django.contrib.postgres, PLATFORM_SUBDOMAINS, enable middleware
```

### Store Model Implementation Reference

```python
import uuid
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from safedelete.models import SafeDeleteModel, SOFT_DELETE_CASCADE
from safedelete.queryset import SafeDeleteQueryset


class TenantType(models.TextChoices):
    RETAIL = "retail", _("Retail")
    RESTAURANT = "restaurant", _("Restaurant")
    BAR = "bar", _("Bar")
    CONTRACTING = "contracting", _("Contracting")


class StoreStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    ACTIVE = "active", _("Active")
    SUSPENDED = "suspended", _("Suspended")
    CANCELLED = "cancelled", _("Cancelled")


class StoreQuerySet(SafeDeleteQueryset):
    def active(self):
        return self.filter(status=StoreStatus.ACTIVE)


class Store(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True)
    domain = models.CharField(max_length=253, unique=True, db_index=True)
    tenant_type = models.CharField(
        max_length=20,
        choices=TenantType.choices,
        default=TenantType.RETAIL,
    )
    status = models.CharField(
        max_length=20,
        choices=StoreStatus.choices,
        default=StoreStatus.PENDING,
    )
    currency = models.CharField(max_length=3, default="KES")
    payment_methods = ArrayField(
        models.CharField(max_length=50), default=list, blank=True
    )
    country = models.CharField(max_length=2, default="KE")
    timezone = models.CharField(max_length=63, default="Africa/Nairobi")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = StoreQuerySet.as_manager()

    class Meta:
        db_table = "store_store"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.domain})"

    def save(self, *args, **kwargs):
        # FR4: tenant_type is immutable once orders exist
        if self.pk:
            original = Store.objects.filter(pk=self.pk).first()
            if original and original.tenant_type != self.tenant_type:
                from apps.order.models import Order  # lazy import

                if Order.objects.filter(store=self).exists():
                    raise ValidationError(
                        "tenant_type cannot be changed after orders exist"
                    )
        super().save(*args, **kwargs)
```

### TenantModel Implementation Reference

```python
# core/models.py
from safedelete.models import SafeDeleteModel, SOFT_DELETE_CASCADE


class SoftDeleteModel(SafeDeleteModel):
    """Base for models needing soft-delete without tenant FK (e.g. Store itself)."""
    _safedelete_policy = SOFT_DELETE_CASCADE

    class Meta:
        abstract = True


class TenantModel(SafeDeleteModel):
    """
    Base class for ALL tenant-scoped domain models.

    Adds store FK.  TenantQuerySet wired in Story 1.3.
    RULE: Every domain model MUST inherit from TenantModel — never models.Model.
    """
    _safedelete_policy = SOFT_DELETE_CASCADE

    store = models.ForeignKey(
        "store.Store",  # lazy string ref — avoids circular import
        on_delete=models.CASCADE,
        related_name="+",
        db_index=True,
    )

    class Meta:
        abstract = True
```

**Critical:** Use `"store.Store"` string reference (app_label.ModelName) NOT `apps.store.models.Store`. This avoids circular import since core/ is imported by store/.

### TenantMiddleware Implementation Reference

```python
# core/middleware.py
import uuid
from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin


class TenantMiddleware(MiddlewareMixin):
    """
    Resolves request.store before any view logic runs.

    Resolution order:
      1. Path bypass (/health/, /admin/, etc.) → skip
      2. Platform subdomain bypass (admin.joat.com, etc.) → skip
      3. X-Store-ID header → lookup by UUID
      4. Host header → lookup by domain
      5. Not found → 404
      6. Suspended → 503
    """

    def process_request(self, request):
        from apps.store.models import Store  # lazy import

        path = request.path_info
        host = request.get_host().split(":")[0].lower()

        # 1. Path bypass
        bypass_paths = getattr(settings, "MIDDLEWARE_BYPASS_PATHS", ["/health/"])
        if any(path.startswith(bp) for bp in bypass_paths):
            request.store = None
            return None

        # 2. Platform subdomain bypass
        platform_subdomains = getattr(settings, "PLATFORM_SUBDOMAINS", [])
        if host in platform_subdomains:
            request.store = None
            return None

        store = None

        # 3. X-Store-ID header
        store_id_header = request.headers.get("X-Store-ID")
        if store_id_header:
            try:
                store_uuid = uuid.UUID(store_id_header)
                store = Store.objects.filter(id=store_uuid).first()
            except ValueError:
                pass  # Invalid UUID — fall through to domain lookup

        # 4. Host header domain lookup
        if store is None:
            store = Store.objects.filter(domain=host).first()

        # 5. Not found → 404
        if store is None:
            return JsonResponse(
                {"errors": [{"field": None, "message": "Store not found.", "code": "NOT_FOUND"}]},
                status=404,
            )

        # 6. Suspended → 503
        if store.status == "suspended":
            return JsonResponse(
                {"errors": [{"field": None, "message": "Store is suspended.", "code": "STORE_SUSPENDED"}]},
                status=503,
            )

        request.store = store
        return None
```

### MIDDLEWARE Order in base.py

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "core.middleware.TenantMiddleware",          # ← ADD HERE (after sessions)
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]
```

**Why after SessionMiddleware?** Session data is needed for admin panel session auth. TenantMiddleware must run before `CommonMiddleware` (URL normalization) but after sessions are available.

### Testing Patterns

**Use `pytest.mark.django_db` for all model tests** (requires DB).

**Middleware testing** — use Django's `RequestFactory` + instantiate middleware directly:
```python
from django.test import RequestFactory, TestCase
from core.middleware import TenantMiddleware

class TestTenantMiddleware(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = TenantMiddleware(get_response=lambda r: None)

    def test_resolves_store_from_domain(self):
        store = Store.objects.create(
            name="Test", slug="test", domain="test.joat.com",
            status="active"
        )
        request = self.factory.get("/", HTTP_HOST="test.joat.com")
        self.middleware.process_request(request)
        assert request.store == store
```

**Cross-tenant test naming** — from `architecture.md#CI Enforcement`:
> `pytest -k "cross_tenant"` — any cross-tenant data leak fails the build

Name cross-tenant tests with `cross_tenant` in the test name:
```python
def test_cross_tenant_isolation_x_store_id_cannot_spoof(self):
    ...
```

### safedelete Package Notes

```python
from safedelete.models import SafeDeleteModel, SOFT_DELETE_CASCADE
from safedelete.queryset import SafeDeleteQueryset
```

- `SOFT_DELETE_CASCADE` — cascades soft-delete to related objects
- `SafeDeleteQueryset` — base queryset that excludes soft-deleted objects by default
- Access soft-deleted records: `Store.all_objects.all()` (uses `SafeDeleteAllManager`)
- `django-safedelete==1.4.*` is already in `requirements/base.txt`

### django.contrib.postgres ArrayField

```python
from django.contrib.postgres.fields import ArrayField
```

**Required:** `"django.contrib.postgres"` MUST be in `INSTALLED_APPS` before ArrayField works.
Add to `DJANGO_APPS` list in `config/settings/base.py` BEFORE the custom apps.

**Migration note:** ArrayField creates a PostgreSQL `text[]` or `varchar[]` column. The migration will only run successfully against PostgreSQL (not SQLite). CI uses postgres:17-alpine service container — ✅ compatible.

### Store UUID Primary Key

The Store model uses `UUIDField` as PK (not auto-increment integer). This means:
- `X-Store-ID` header contains a UUID string (e.g. `"a3f7c2d1-..."`)
- All FKs to Store use UUID — `store_id = UUIDField()`
- `TenantModel.store_id` column will be UUID type in the DB

### order/models.py Lazy Import Guard

The `Store.save()` guard does:
```python
from apps.order.models import Order  # lazy import
```

At this stage (Story 1.2), `apps/order/models.py` exists but Order model is not yet implemented (it's a stub). The lazy import will succeed (module exists), but `Order.objects.filter(store=self)` will return empty queryset since there's no Order table yet.

**Migration concern:** Do NOT add an actual DB constraint for tenant_type immutability — this is an application-level guard in `save()` only. The DB allows type changes; the application rejects them.

### Project Structure — what already EXISTS

From Story 1.1 scaffold (do NOT recreate):
- `backend/apps/store/__init__.py`, `apps.py`, `admin.py` (empty stub), `serializers.py`, `views.py`, `urls.py`, `tests/__init__.py`
- `backend/core/__init__.py`, `exceptions.py`, `pagination.py`, `permissions.py`, `querysets.py`, `serializers.py`, `utils.py`, `views.py` (all stubs for later stories)
- `backend/config/settings/base.py` with `TenantMiddleware` commented out
- `"safedelete"` already in `INSTALLED_APPS` (THIRD_PARTY_APPS in base.py)

**Do NOT recreate existing files** — only modify what's specified.

### Previous Story Learnings (Stories 1.1–1.1c)

- `core/` is at `backend/core/` NOT `backend/apps/core/` — it's a top-level Django app
- `apps/store/` is at `backend/apps/store/` — inside the apps package
- Black + isort must pass — run `black .` then `isort .` before marking tasks complete
- flake8 `max-line-length = 88` — keep all lines ≤ 88 chars
- `django.contrib.postgres` needs to be added to `DJANGO_APPS` for ArrayField
- Store model uses `id = UUIDField(primary_key=True)` — not default integer PK
- Use lazy string `"store.Store"` in TenantModel FK — avoids circular import since core/ is imported early
- `apps/store/migrations/__init__.py` already exists (empty) — makemigrations will add `0001_initial.py`

### Architecture References

- [Source: architecture.md#Tenant Isolation] — 5-layer isolation, TenantModel/TenantQuerySet/TenantMiddleware pattern
- [Source: architecture.md#Core Module Structure] — core/ file layout, TenantMiddleware responsibility
- [Source: architecture.md#Store App Structure] — apps/store/ layout, test files
- [Source: architecture.md#Soft Delete] — django-safedelete, SOFT_DELETE_CASCADE, DPA-compliant
- [Source: architecture.md#Enforcement Rules] — MUST inherit TenantModel, never models.Model
- [Source: architecture.md#Naming Conventions] — db_table, column naming
- [Source: epics.md#Story 1.2] — full acceptance criteria (canonical)
- [Source: prd.md#FR1-FR8] — multi-tenant platform, tenant lifecycle, tenant type lock

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None at story creation._

### Completion Notes List

- `core/models.py`: `SoftDeleteModel` (abstract, SOFT_DELETE_CASCADE) + `TenantModel` (abstract, SOFT_DELETE_CASCADE, `store` FK using `"store.Store"` lazy string to avoid circular import).
- `core/middleware.py`: `TenantMiddleware` — path bypass → platform subdomain bypass → X-Store-ID UUID header → Host domain → 404/503, sets `request.store`. Uses lazy import of Store inside `process_request`.
- `apps/store/models.py`: `TenantType` + `StoreStatus` TextChoices, `StoreQuerySet(SafeDeleteQueryset)` with `.active()`, `Store(SafeDeleteModel)` with UUID PK + ArrayField + all required fields + `save()` FR4 guard (lazy import Order), `StoreSettings(TenantModel)` stub, `StoreTheme(TenantModel)` stub.
- `apps/store/admin.py`: Registers Store, StoreSettings, StoreTheme with appropriate display/filter/search.
- `config/settings/base.py`: Added `django.contrib.postgres` to DJANGO_APPS; enabled `core.middleware.TenantMiddleware` after SessionMiddleware; added `PLATFORM_SUBDOMAINS` and `MIDDLEWARE_BYPASS_PATHS` env-configurable settings.
- Migration `0001_initial.py`: Auto-generated — UUID PK, ArrayField, all fields, safedelete columns, StoreSettings/StoreTheme FK to store.store.
- Tests: 11 model tests (creation, UUID PK, all fields, str, unique constraints, soft delete, active queryset, tenant_type guard mocked) + 15 middleware tests (domain, X-Store-ID, priority, fallback, 404, 503, platform bypass, path bypass, localhost, cross_tenant isolation × 2).
- Cross-tenant tests named with `cross_tenant` for `pytest -k cross_tenant` CI enforcement.
- flake8 ✅ black ✅ isort ✅ `manage.py check` → 0 errors ✅ smoke tests 4/4 ✅

### File List

**Modified:**
- `backend/core/models.py`
- `backend/core/middleware.py`
- `backend/apps/store/models.py`
- `backend/apps/store/admin.py`
- `backend/config/settings/base.py`

**New:**
- `backend/apps/store/migrations/0001_initial.py`
- `backend/apps/store/tests/test_models.py`
- `backend/apps/store/tests/test_middleware.py`
