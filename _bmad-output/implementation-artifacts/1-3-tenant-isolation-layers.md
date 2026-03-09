# Story 1.3: Tenant Isolation Layers

Status: ready-for-dev

---

## Story

As a store staff member,
I want all API responses to only ever contain data belonging to my store,
So that I can never accidentally see or modify another tenant's data.

---

## Acceptance Criteria

**AC1 — IsStoreScoped permission stub**

Given any API endpoint that returns store-scoped data
When `IsStoreScoped` permission class is applied and the authenticated user's `store_id` JWT claim does not match `request.store.id`
Then HTTP 403 is returned

_Story 1.3 note:_ `IsStoreScoped` is implemented as a **stub** that allows all authenticated requests for now. The full JWT claim check is added in Story 1.5. The stub must exist and be wirable as `permission_classes = [IsStoreScoped]` in `TenantViewSet`.

**AC2 — TenantSerializer auto-populates store**

Given any DRF serializer inheriting from `TenantSerializer`
When a create or update operation is performed
Then the `store` field is automatically populated from `request.store` and cannot be overridden by client-supplied data

**AC3 — StoreAdmin base class scopes admin views**

Given any Django admin class inheriting from `StoreAdmin`
When a store staff member views any list or detail page
Then only records belonging to their own store are returned — no cross-tenant data ever visible

**AC4 — TenantQuerySet raises DoesNotExist on cross-tenant access**

Given a `TenantQuerySet` applied as default manager on any model
When a cross-tenant `.get(id=<other_store_record_id>)` is attempted
Then `DoesNotExist` is raised rather than the record being returned

**AC5 — Cross-tenant test suite passes**

Given the cross-tenant isolation test suite
When `pytest -k "cross_tenant"` is run
Then all tests pass, covering: middleware resolution, queryset filtering, permission enforcement, serializer auto-population
And this suite is registered as a CI gate on every PR touching models or views

**AC6 — UUID primary keys on TenantModel**

Given any model that is accessible via a public-facing API endpoint
When its primary key is inspected
Then it is a UUID — auto-incrementing integer IDs are never exposed in any API response or URL path
And this is enforced by `TenantModel` setting `id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`

---

## ⚠️ Scope Boundaries — What This Story Does NOT Include

| Out of scope | Handled in |
|---|---|
| IsStoreScoped full JWT claim check | Story 1.5 |
| IsPlatformAdmin, IsStoreOwner, IsStoreManager | Story 1.5 |
| custom_exception_handler full implementation | Story 1.6 |
| StoreSettings + StoreTheme full branding fields | Story 1.7 |
| Store provisioning REST API | Story 1.4 |
| JWT token issuance and refresh | Story 1.5 |
| Any domain model (Product, Order, etc.) | Epic 3+ |

---

## Tasks / Subtasks

- [ ] **Task 1: Implement `core/querysets.py` — TenantQuerySet** (AC: 4, 5, 6)
  - [ ] Implement `TenantQuerySet(SafeDeleteQueryset)`:
    - Inherits from `SafeDeleteQueryset` (django-safedelete)
    - Override `get_queryset()` pattern: auto-filters by `store_id` when `request.store` is available in context
    - **Key method:** `for_store(store)` — filters queryset to `store_id=store.pk`
    - Cross-tenant `.get()` will raise `DoesNotExist` automatically because the queryset is pre-filtered
  - [ ] `TenantQuerySet` does NOT hold a reference to `request` — it is a plain queryset; the view calls `.for_store(request.store)` or `TenantViewSet.get_queryset()` handles it

- [ ] **Task 2: Update `core/models.py` — add UUID PK to TenantModel** (AC: 6)
  - [ ] Modify `TenantModel` to add `id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`
  - [ ] All models that inherit `TenantModel` will automatically get UUID PKs — no per-model override needed
  - [ ] `import uuid` must be added to `core/models.py`

- [ ] **Task 3: Implement `core/serializers.py` — TenantSerializer** (AC: 2, 5)
  - [ ] Implement `TenantSerializer(serializers.ModelSerializer)`:
    - Override `create()`: injects `store = self.context["request"].store` into `validated_data` before save
    - Override `to_internal_value()`: strips `store` / `store_id` from incoming data so clients cannot override it
    - `store` field is excluded from all serializer field lists (never in `Meta.fields` or responses)
  - [ ] **Context requirement:** All views using `TenantSerializer` subclasses must pass `{"request": request}` as serializer context — `TenantViewSet` handles this automatically

- [ ] **Task 4: Implement `core/pagination.py` — StoreCursorPagination** (AC: 5)
  - [ ] Implement `StoreCursorPagination(CursorPagination)`:
    - `page_size = 20`
    - `max_page_size = 100`
    - `ordering = "-created_at"` (default; overridable per viewset)
    - Override `get_paginated_response()` to return `{data: [...], meta: {count, next, previous}}`
    - Override `get_paginated_response_schema()` for OpenAPI (optional stub)
  - [ ] Import from `rest_framework.pagination import CursorPagination`

- [ ] **Task 5: Implement `core/views.py` — TenantViewSet** (AC: 1, 2, 4, 5)
  - [ ] Implement `TenantViewSet(viewsets.ModelViewSet)`:
    - `pagination_class = StoreCursorPagination`
    - `permission_classes = [IsStoreScoped]` — uses stub from Task 6
    - Override `get_queryset()`:
      - Takes the declared `queryset` class attribute
      - Calls `.for_store(self.request.store)` on it
      - Returns filtered queryset
    - Override `perform_create(serializer)`:
      - Calls `serializer.save(store=self.request.store)`
    - Override `get_serializer_context()`:
      - Returns `{**super().get_serializer_context(), "request": self.request}` to ensure `TenantSerializer` has request context
  - [ ] **RULE:** All domain viewsets MUST extend `TenantViewSet` — never `ModelViewSet` directly

- [ ] **Task 6: Implement `core/permissions.py` — IsStoreScoped stub** (AC: 1, 5)
  - [ ] Implement `IsStoreScoped(BasePermission)` as a **stub**:
    - `has_permission(self, request, view)` returns `True` for all requests (Story 1.5 adds JWT check)
    - Include a `# TODO: Story 1.5 — check request.user.store_id == request.store.id` comment
  - [ ] Do NOT implement `IsPlatformAdmin`, `IsStoreOwner`, `IsStoreManager` — those are Story 1.5
  - [ ] This stub must be importable and usable as `permission_classes = [IsStoreScoped]`

- [ ] **Task 7: Implement `core/admin.py` — StoreAdmin base class** (AC: 3, 5)
  - [ ] Create `backend/core/admin.py` (new file):
    - Implement `StoreAdmin(admin.ModelAdmin)`:
      - Override `get_queryset(self, request)`:
        - If `request.store` is set, filter to `store=request.store`
        - If `request.store` is None (platform admin), return full queryset
      - This stub is minimal — Story 1.5 adds full RBAC checks
  - [ ] Do NOT register any models in `core/admin.py` — each app registers its own models

- [ ] **Task 8: Write tests** (AC: 1–6)
  - [ ] Create `backend/core/tests/` directory with `__init__.py`
  - [ ] Create `backend/core/tests/test_querysets.py`:
    - `test_tenant_queryset_filters_by_store`: creates 2 stores + 1 record each; `.for_store(store_a)` returns only store_a's record
    - `test_cross_tenant_queryset_get_raises_does_not_exist`: `.for_store(store_a).get(pk=store_b_record.pk)` raises `DoesNotExist`
    - `test_cross_tenant_isolation_queryset_never_leaks_records` (CI gate — named with `cross_tenant`)
  - [ ] Create `backend/core/tests/test_serializers.py`:
    - `test_tenant_serializer_injects_store_on_create`: store not in request body → still set from request context
    - `test_tenant_serializer_cannot_override_store`: client-supplied `store_id` is stripped
    - `test_cross_tenant_isolation_serializer_cannot_set_foreign_store` (CI gate)
  - [ ] Create `backend/core/tests/test_pagination.py`:
    - `test_cursor_pagination_returns_data_meta_envelope`: response has `data` list + `meta` with `count`, `next`, `previous`
    - `test_cursor_pagination_default_page_size`: default page size is 20
  - [ ] Create `backend/core/tests/test_views.py`:
    - Uses a minimal concrete viewset subclassing `TenantViewSet` with a test model (or mock)
    - `test_tenant_viewset_scopes_queryset_to_request_store`
    - `test_tenant_viewset_perform_create_injects_store`
    - `test_cross_tenant_isolation_viewset_cannot_read_other_store_record` (CI gate)

- [ ] **Task 9: Validate** (AC: 1–6)
  - [ ] `python manage.py check` → 0 errors
  - [ ] `python -m pytest core/tests/ -v` → all tests pass
  - [ ] `python -m pytest -k "cross_tenant" -v` → all cross-tenant tests pass
  - [ ] `python -m flake8 core/` → 0 violations
  - [ ] `python -m black --check core/` → 0 changes
  - [ ] `python -m isort --check-only core/` → clean

---

## Dev Notes

### Core Architecture — Read This First

From `architecture.md#Tenant Isolation`:

**5-layer tenant isolation (implement ALL in sequence):**
1. **Middleware** — `request.store` resolved before any view → Story 1.2 ✅
2. **Base queryset** — `TenantQuerySet` auto-filters by `store_id` → **this story** ✅
3. **Serializer** — auto-injects store on create → **this story** ✅
4. **Permission class** — `IsStoreScoped` validates user belongs to request.store → Story 1.5 (stub here)
5. **Admin** — `StoreAdmin` base class scopes admin views → **this story (stub)** ✅

**Rule:** Every domain viewset MUST extend `TenantViewSet` — never `ModelViewSet` directly.

### File Locations

```
backend/
├── core/
│   ├── models.py         # MODIFY — add UUID PK to TenantModel
│   ├── querysets.py      # MODIFY — implement TenantQuerySet
│   ├── serializers.py    # MODIFY — implement TenantSerializer
│   ├── views.py          # MODIFY — implement TenantViewSet
│   ├── pagination.py     # MODIFY — implement StoreCursorPagination
│   ├── permissions.py    # MODIFY — implement IsStoreScoped stub
│   ├── admin.py          # CREATE — StoreAdmin base class
│   └── tests/
│       ├── __init__.py   # CREATE
│       ├── test_querysets.py    # CREATE
│       ├── test_serializers.py  # CREATE
│       ├── test_pagination.py   # CREATE
│       └── test_views.py        # CREATE
```

### TenantQuerySet Implementation Reference

```python
# core/querysets.py
from safedelete.queryset import SafeDeleteQueryset


class TenantQuerySet(SafeDeleteQueryset):
    """
    Base queryset for all tenant-scoped models.
    Prevents cross-tenant data leakage at the ORM layer.

    Usage:
        class ProductQuerySet(TenantQuerySet):
            pass

        class Product(TenantModel):
            objects = ProductQuerySet.as_manager()
    """

    def for_store(self, store):
        """Filter queryset to records belonging to the given store."""
        return self.filter(store_id=store.pk)
```

**How cross-tenant protection works:**
- `TenantViewSet.get_queryset()` calls `.for_store(request.store)` — scope is set once per request
- Any `.get(pk=some_uuid)` called on the scoped queryset will only find records within `request.store`
- A cross-tenant `.get(pk=other_store_record)` raises `DoesNotExist` — not 403, not wrong data — just not found

### TenantModel UUID PK Reference

```python
# core/models.py
import uuid

from django.db import models
from safedelete.models import SOFT_DELETE_CASCADE, SafeDeleteModel


class SoftDeleteModel(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE

    class Meta:
        abstract = True


class TenantModel(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(
        "store.Store",
        on_delete=models.CASCADE,
        related_name="+",
        db_index=True,
    )

    class Meta:
        abstract = True
```

**Note:** `Store` itself does NOT inherit `TenantModel` (it IS the tenant root). `Store` already has `id = UUIDField(primary_key=True)` defined directly in `apps/store/models.py`.

### TenantSerializer Implementation Reference

```python
# core/serializers.py
from rest_framework import serializers


class TenantSerializer(serializers.ModelSerializer):
    """
    Base serializer for all tenant-scoped models.

    Automatically:
      - Injects store from request context on create
      - Strips client-supplied store/store_id to prevent override
      - Never exposes store_id in API responses
    """

    def to_internal_value(self, data):
        # Strip store/store_id from incoming data — client cannot set it
        data = data.copy() if hasattr(data, "copy") else dict(data)
        data.pop("store", None)
        data.pop("store_id", None)
        return super().to_internal_value(data)

    def create(self, validated_data):
        # Inject store from request context
        request = self.context.get("request")
        if request and hasattr(request, "store") and request.store:
            validated_data["store"] = request.store
        return super().create(validated_data)
```

### StoreCursorPagination Implementation Reference

```python
# core/pagination.py
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response


class StoreCursorPagination(CursorPagination):
    """
    Cursor-based pagination for all store-scoped list endpoints.
    Cursor pagination is stable under concurrent writes.

    Response envelope:
      {
        "data": [...],
        "meta": {
          "count": 150,
          "next": "cursor_token_or_null",
          "previous": "cursor_token_or_null"
        }
      }
    """

    page_size = 20
    max_page_size = 100
    ordering = "-created_at"

    def get_paginated_response(self, data):
        return Response(
            {
                "data": data,
                "meta": {
                    "count": self.page.paginator.count,
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                },
            }
        )
```

**Note on count:** `CursorPagination` does not provide a `count` by default (it avoids COUNT(*) for performance). If `self.page.paginator.count` raises an error, use `None` for count and document it as a known limitation. Story 8.3 (per-store analytics API) will address total counts via pre-aggregated summaries.

### TenantViewSet Implementation Reference

```python
# core/views.py
from rest_framework import viewsets

from core.pagination import StoreCursorPagination
from core.permissions import IsStoreScoped


class TenantViewSet(viewsets.ModelViewSet):
    """
    Base viewset for all tenant-scoped endpoints.

    Automatically:
      - Scopes get_queryset() to request.store
      - Injects store into perform_create()
      - Uses StoreCursorPagination
      - Uses IsStoreScoped permission (stub — full check in Story 1.5)

    RULE: All domain viewsets MUST inherit TenantViewSet.
    """

    pagination_class = StoreCursorPagination
    permission_classes = [IsStoreScoped]

    def get_queryset(self):
        qs = super().get_queryset()
        if hasattr(qs, "for_store") and self.request.store:
            return qs.for_store(self.request.store)
        return qs

    def perform_create(self, serializer):
        serializer.save(store=self.request.store)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context
```

### IsStoreScoped Stub Implementation Reference

```python
# core/permissions.py
from rest_framework.permissions import BasePermission


class IsStoreScoped(BasePermission):
    """
    Verifies the authenticated user belongs to request.store.

    Story 1.3: STUB — allows all requests (JWT check added in Story 1.5).
    Story 1.5 will check: request.user.store_id == request.store.id
    """

    def has_permission(self, request, view):
        # TODO: Story 1.5 — check request.user.store_id == request.store.id
        return True  # stub: allow all for now
```

### StoreAdmin Base Class Reference

```python
# core/admin.py
from django.contrib import admin


class StoreAdmin(admin.ModelAdmin):
    """
    Base admin class that scopes list/detail views to request.store.

    Story 1.3: STUB — filters by store if request.store is set.
    Story 1.5 adds full RBAC checks (platform_admin sees all, store_owner sees own).
    """

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if hasattr(request, "store") and request.store:
            return qs.filter(store=request.store)
        return qs
```

### API Response Envelope Pattern

From `architecture.md`:

```json
// Single object success
{ "data": { "id": "uuid", "name": "iPhone Charger", "price": "1500.00" } }

// List success (cursor pagination)
{ "data": [...], "meta": { "count": 142, "next": "cD0yMDI2...", "previous": null } }

// Validation error (422)
{ "errors": [{ "field": "phone", "message": "Must be a valid Kenyan phone number.", "code": "INVALID_PHONE" }] }
```

**Rule:** Use the `{data, meta, errors}` envelope — never bare objects. `StoreCursorPagination.get_paginated_response()` handles the list envelope. Single-object responses are wrapped by the custom exception handler (Story 1.6).

### Cross-Tenant Test Suite Requirements

From `architecture.md#CI Enforcement`:
> `pytest -k "cross_tenant"` — any cross-tenant data leak fails the build

Tests in this suite MUST be named with `cross_tenant` in the function name:

```python
def test_cross_tenant_isolation_queryset_never_leaks_records(self):
    """TenantQuerySet never returns records from another store."""
    store_a = make_store(domain="a.joat.com")
    store_b = make_store(domain="b.joat.com")
    # create a test record for store_b using a concrete model
    ...
    results = SomeModel.objects.for_store(store_a)
    assert not results.filter(store=store_b).exists()
```

**Test model strategy:** Use `apps.store.models.StoreSettings` (a real `TenantModel` subclass already created in Story 1.2) as the concrete model for queryset/serializer tests. This avoids creating a dedicated test model.

### Testing: Using StoreSettings as Concrete TenantModel

`StoreSettings` from `apps.store.models` is available, inherits `TenantModel`, and exists in the DB after Story 1.2 migration. Use it for testing:

```python
from apps.store.models import StoreSettings

def test_cross_tenant_isolation_queryset_never_leaks_records(self):
    store_a = make_store(domain="a.joat.com")
    store_b = make_store(domain="b.joat.com")
    settings_b = StoreSettings.objects.create(store=store_b)

    # Scope queryset to store_a — store_b record must not appear
    qs = StoreSettings.objects.for_store(store_a)
    assert not qs.filter(pk=settings_b.pk).exists()
```

**Important:** `StoreSettings` uses `TenantModel.objects` which is a plain Manager (not `TenantQuerySet`) until we wire it up. In Story 1.3 we update `TenantModel` — but `StoreSettings` inherits the manager from `TenantModel`. To test `TenantQuerySet` directly, we can add `objects = TenantQuerySet.as_manager()` to `TenantModel` in this story.

### Wiring TenantQuerySet as Default Manager on TenantModel

The cleanest approach is to set `TenantQuerySet` as the default manager on `TenantModel` itself:

```python
# core/models.py
from core.querysets import TenantQuerySet  # no circular import — same package

class TenantModel(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(
        "store.Store",
        on_delete=models.CASCADE,
        related_name="+",
        db_index=True,
    )

    objects = TenantQuerySet.as_manager()

    class Meta:
        abstract = True
```

**Circular import check:** `core/querysets.py` imports only `safedelete` — no risk. `core/models.py` imports `core/querysets.py` — safe (same package, no circular dependency).

**safedelete compatibility:** `TenantQuerySet` inherits from `SafeDeleteQueryset` so safedelete's soft-delete filtering is preserved. `TenantQuerySet.as_manager()` creates a manager that includes all safedelete manager methods.

### Migration Note

`TenantModel` is abstract — adding `id = UUIDField(primary_key=True)` to it requires a new migration for `StoreSettings` and `StoreTheme` (the only concrete `TenantModel` subclasses at this point). Run:

```bash
python manage.py makemigrations store --name="add_uuid_pk_to_tenant_models"
```

The migration will add UUID PKs to `store_storesettings` and `store_storetheme` tables. Inspect before applying.

### Previous Story Learnings (Stories 1.1–1.2)

- `core/` is at `backend/core/` — top-level Django app, NOT `backend/apps/core/`
- Black line-length 88; run `black .` then `isort .` before marking tasks done
- flake8 `max-line-length = 88` — keep all lines ≤ 88 chars (docstrings and comments too)
- No `import` in `__init__.py` unless explicitly required (avoids F401)
- `pytest.mark.django_db` required on all tests that touch the DB
- `apps/store/tests/test_middleware.py` already has cross-tenant tests — DO NOT duplicate; add new cross-tenant tests in `core/tests/` for queryset/serializer/viewset isolation
- `manage.py check` must return 0 errors before marking any task done

### Architecture References

- [Source: architecture.md#Tenant Isolation] — 5-layer isolation pattern
- [Source: architecture.md#Implementation Patterns] — TenantViewSet example (correct vs wrong)
- [Source: architecture.md#Enforcement Guidelines] — mandatory rules for all agents
- [Source: architecture.md#API Response Envelope] — {data, meta, errors} contract
- [Source: architecture.md#StoreCursorPagination] — cursor pagination, default 20, max 100
- [Source: epics.md#Story 1.3] — 6 acceptance criteria (canonical)
- [Source: prd.md#FR5] — tenant isolation at 5 layers

---

## Dev Agent Record

### Agent Model Used

_To be filled in by dev agent._

### Debug Log References

_None at story creation._

### Completion Notes List

_To be filled in by dev agent._

### File List

**Modified:**
- `backend/core/models.py`
- `backend/core/querysets.py`
- `backend/core/serializers.py`
- `backend/core/views.py`
- `backend/core/pagination.py`
- `backend/core/permissions.py`

**New:**
- `backend/core/admin.py`
- `backend/core/tests/__init__.py`
- `backend/core/tests/test_querysets.py`
- `backend/core/tests/test_serializers.py`
- `backend/core/tests/test_pagination.py`
- `backend/core/tests/test_views.py`

**Possibly new (migration):**
- `backend/apps/store/migrations/0002_add_uuid_pk_to_tenant_models.py`
