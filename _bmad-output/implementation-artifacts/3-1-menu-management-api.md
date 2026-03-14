# Story 3.1: Menu Management API

Status: done

## Story

As a restaurant store owner,
I want to manage my menu with sections, items, modifiers, allergen flags, and time-based scheduling,
So that my customers always see an accurate, correctly priced menu for the current service period.

## Acceptance Criteria

**AC1 — MenuSection + MenuItem + ModifierGroup + Modifier models**

Given a restaurant store owner is authenticated
When they create a MenuSection (e.g. "Starters"), MenuItem under it, and ModifierGroup with Modifier items
Then all are stored scoped to their store and ModifierGroup min/max selection rules are stored

**AC2 — Time-based availability filtering**

Given a MenuItem has available_from and available_until times set (e.g. breakfast 06:00–11:00)
When a customer views the menu outside that window
Then the item is automatically hidden from the API response — no client-side filtering required

**AC3 — Allergen flag**

Given a MenuItem has contains_allergens=True
When it is returned via any menu API endpoint
Then an allergen flag is included in the response

**AC4 — Modifier price addition**

Given a Modifier has price_addition > 0
When a customer selects it
Then the modifier price is included in the response for client-side total recalculation

**AC5 — Tenant isolation**

All menu models are scoped to request.store — cross-tenant queries are impossible via the API

## Tasks/Subtasks

- [x] Task 1: Menu models (MenuSection, MenuItem, ModifierGroup, Modifier)
  - [x] 1a: models.py with all four models
  - [x] 1b: initial migration
- [x] Task 2: Serializers (nested read + write)
- [x] Task 3: Views + URLs (CRUD, time-based filtering)
- [x] Task 4: Tests (models, views, time-filtering, allergen flag, modifier price)

## Dev Notes

- All models inherit TenantModel (UUID PK, store FK, soft-delete)
- Time-based filtering: compare available_from / available_until against current time in get_queryset
- available_from / available_until are TimeField (nullable) — null means always available
- ModifierGroup.min_selections default 0, max_selections default 1
- Use TenantViewSet base for all views
- Tests use factory-boy factories

## Dev Agent Record

### Implementation Plan
Story 3.1 — Menu Management API

### Debug Log
N/A

### Completion Notes
Implemented MenuSection, MenuItem, ModifierGroup, Modifier models with full CRUD API.
Time-based availability filtering in get_queryset. Allergen flag and modifier price_addition
in serializer responses. 18 tests covering all ACs.

## File List

- backend/apps/restaurant/models.py
- backend/apps/restaurant/migrations/0001_initial.py
- backend/apps/restaurant/serializers.py
- backend/apps/restaurant/views.py
- backend/apps/restaurant/urls.py
- backend/apps/restaurant/tests/__init__.py
- backend/apps/restaurant/tests/factories.py
- backend/apps/restaurant/tests/test_models.py
- backend/apps/restaurant/tests/test_views.py

## Change Log

- 2026-03-14: Story 3.1 implemented — menu models, CRUD API, time-based filtering, allergen flag, tests
