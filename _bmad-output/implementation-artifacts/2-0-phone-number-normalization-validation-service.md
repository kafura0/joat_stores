# Story 2.0: Phone Number Normalization + Validation Service

Status: done

---

## Story

As a payment system,
I want all phone numbers normalized to E.164 format before any M-Pesa or SMS operation,
So that Kenyan numbers in any local format (`07XX`, `+254XX`, `254XX`) always reach Daraja correctly.

---

## Acceptance Criteria

**AC1 — KE local format (07XX)**

Given `normalize_phone('0712345678', country_code='KE')` is called
When executed
Then the return value is `'+254712345678'`

**AC2 — KE without leading `+` (254XX)**

Given `normalize_phone('254712345678', country_code='KE')` is called
When executed
Then the return value is `'+254712345678'`

**AC3 — KE already E.164 (`+254XX`)**

Given `normalize_phone('+254712345678', country_code='KE')` is called
When executed
Then the return value is `'+254712345678'` unchanged

**AC4 — Invalid KE prefix raises PhoneNormalizationError**

Given `normalize_phone('0812345678', country_code='KE')` is called
When executed
Then `PhoneNormalizationError` is raised with a descriptive message
And the number is never passed to Daraja or any downstream API

**AC5 — JM format (multi-country)**

Given `normalize_phone('8761234567', country_code='JM')` is called
When executed
Then the return value is `'+18761234567'`

**AC6 — Raw phones never reach Daraja/WhatsApp/SMS**

Given any payment or SMS notification flow passes a phone number
When the number is processed
Then it always passes through `normalize_phone()` first
And raw phone strings never reach Daraja, WhatsApp, or SMS APIs directly

**AC7 — `normalise_mpesa_phone()` in `core/utils.py` delegates to `normalize_phone`**

Given `normalise_mpesa_phone('0712345678')` is called
When executed
Then it returns `'+254712345678'` — calling `normalize_phone(raw, country_code='KE')` internally
And the existing architecture enforcement rule ("use `normalise_mpesa_phone()` from `core/utils.py`") continues to hold for all callers

---

## Tasks / Subtasks

- [x] **Task 1: Create `apps/payment/phone.py`** (AC: 1, 2, 3, 4, 5, 6)
  - [x] Define `PhoneNormalizationError(ValueError)` with attributes: `raw_phone: str`, `country_code: str`, `message: str`
  - [x] Implement `normalize_phone(raw_phone: str, country_code: str = 'KE') -> str`
    - [x] KE branch: strip non-digits; handle `07XXXXXXXX` (10 digits → prefix `+254`), `254XXXXXXXXX` (12 digits → prefix `+`), `+254XXXXXXXXX` (already E.164); raise `PhoneNormalizationError` for anything else
    - [x] JM branch: handle `876XXXXXXX` (10 digits → `+1876XXXXXXX`), `1876XXXXXXX` (11 digits → prefix `+`), `+1876XXXXXXX` (already E.164); raise for anything else
    - [x] Unsupported `country_code` → raise `PhoneNormalizationError` with code `UNSUPPORTED_COUNTRY`
    - [x] Pure function — zero Django imports, zero side effects, importable without Django setup

- [x] **Task 2: Update `core/utils.py`** (AC: 7)
  - [x] Implement `normalise_mpesa_phone(raw: str) -> str` — thin delegate: `return normalize_phone(raw, country_code='KE')`
  - [x] Import: `from apps.payment.phone import normalize_phone, PhoneNormalizationError`
  - [x] Re-export `PhoneNormalizationError` from `core/utils.py` so callers don't need to know the implementation module
  - [x] **Do NOT implement `mask_pii` or `format_currency`** — those TODO stubs belong to Story 1.6 (separate concern, not this story's scope)

- [x] **Task 3: Write tests in `apps/payment/tests/test_phone.py`** (AC: 1, 2, 3, 4, 5, 6, 7)
  - [x] Parametrized happy-path tests: all three KE formats → `+254712345678`
  - [x] Parametrized happy-path tests: JM formats → `+18761234567`
  - [x] Invalid KE prefix (`0812345678`, `0912345678`, etc.) → `PhoneNormalizationError` raised
  - [x] Empty string → `PhoneNormalizationError` raised
  - [x] Whitespace / non-numeric garbage input → `PhoneNormalizationError` raised
  - [x] Unsupported country code (`country_code='US'`) → `PhoneNormalizationError` raised
  - [x] `normalise_mpesa_phone('0712345678')` → `'+254712345678'` (integration: delegates correctly)
  - [x] Test that `normalize_phone` is importable with no Django setup (no `@pytest.mark.django_db` needed — pure unit tests)

### Review Follow-ups (AI)

- [ ] [AI-Review][LOW] `PhoneNormalizationError.raw_phone` stores raw PII — enforce `mask_pii()` at call sites once `core/utils.py` TODO is resolved (`core/phone.py:34`)
- [ ] [AI-Review][LOW] `test_normalise_mpesa_phone_raises_on_invalid` — add `pytest.raises(ValueError)` assertion to fully verify shim contract (`test_phone.py:154`)
- [ ] [AI-Review][LOW] Asymmetric handler design — add `_jm_validate_area_code()` helper mirroring KE pattern; document extension point in `_COUNTRY_HANDLERS` for future country additions (`core/phone.py:148`)

---

## Dev Notes

### Critical Architecture Decision — Two-Layer Design

The architecture enforcement rule says:
> "Use `normalise_mpesa_phone()` from `core/utils.py` — never inline phone normalisation"

Story 2.0 places the _implementation_ in `apps/payment/phone.py` (multi-country, raises `PhoneNormalizationError`). The `core/utils.py` becomes the **canonical caller-facing alias** for all existing and future KE callers. This preserves the enforcement rule while giving the payment module ownership of the logic.

```
Caller → normalise_mpesa_phone() in core/utils.py
             ↓ delegates
         normalize_phone(raw, country_code='KE') in apps/payment/phone.py
```

### `PhoneNormalizationError` Design

```python
# apps/payment/phone.py
class PhoneNormalizationError(ValueError):
    def __init__(self, raw_phone: str, country_code: str, message: str):
        self.raw_phone = raw_phone        # never log raw — mask for PII
        self.country_code = country_code
        self.message = message
        super().__init__(message)
```

Do NOT use Django's `ValidationError` — this module must be Django-free.

### KE Validation Rules

```
Valid inputs (strip non-digits first):
  "07XXXXXXXX"      → 10 digits, starts with 0 → replace leading 0 with +254
  "2547XXXXXXXX"    → 12 digits, starts with 254 → prepend +
  "+2547XXXXXXXX"   → 13 chars, starts with + → already E.164, return as-is

Invalid:
  "0812345678"  → 08 prefix does not exist for KE mobile (Safaricom: 07, Airtel: 01)
  "0912345678"  → same
  Length mismatch after stripping non-digits
```

**No carrier filtering at this layer** — just format normalization. Carrier validation (Safaricom-only STK Push) happens in `daraja.py` (Story 2.1).

### JM Validation Rules

```
Valid inputs (strip non-digits first):
  "876XXXXXXX"   → 10 digits → prepend +1
  "1876XXXXXXX"  → 11 digits → prepend +
  "+1876XXXXXXX" → 12 chars → already E.164, return as-is
```

### `core/utils.py` Current State — Important

`core/utils.py` currently has two **unfulfilled TODO stubs**:
```python
# TODO: Story 1.2 — implement normalise_mpesa_phone   ← THIS story implements this
# TODO: Story 1.6 — implement mask_pii, format_currency  ← NOT this story's scope
```
Story 1.6 is marked `done` in sprint tracking but `mask_pii` / `format_currency` were evidently never implemented in `utils.py` (they may be in `core/audit.py` instead — check before touching). This story ONLY implements `normalise_mpesa_phone`. Leave other TODOs untouched.

### Test Pattern — No Django DB Required

These are pure unit tests. Do NOT use `@pytest.mark.django_db`. Do NOT use factory-boy. No fixtures needed.

```python
# apps/payment/tests/test_phone.py
import pytest
from apps.payment.phone import normalize_phone, PhoneNormalizationError

@pytest.mark.parametrize("raw,expected", [
    ("0712345678", "+254712345678"),
    ("254712345678", "+254712345678"),
    ("+254712345678", "+254712345678"),
])
def test_ke_normalization(raw, expected):
    assert normalize_phone(raw, country_code="KE") == expected

@pytest.mark.parametrize("raw", ["0812345678", "0912345678", "123", ""])
def test_ke_invalid_raises(raw):
    with pytest.raises(PhoneNormalizationError):
        normalize_phone(raw, country_code="KE")
```

### Architecture Constraints

- **Pure function** — no Django models, no `request`, no celery, no Redis. Import cost: zero.
- **File location:** `backend/apps/payment/phone.py` (not `core/utils.py` — that's the alias layer)
- `PhoneNormalizationError` must be a `ValueError` subclass so it integrates cleanly with DRF validation in future stories (Story 2.2 will catch it and return HTTP 422)
- The function will be called by Story 2.2 (`initiate_payment`) and every future SMS/WhatsApp dispatch — getting the interface right now prevents mass refactors later

### Existing Files to Check / Modify

| File | Action |
|---|---|
| `backend/apps/payment/phone.py` | **CREATE** — PhoneNormalizationError + normalize_phone |
| `backend/apps/payment/tests/test_phone.py` | **CREATE** — full parametrized test suite |
| `backend/core/utils.py` | **MODIFY** — implement normalise_mpesa_phone (replace TODO) |

### Files to NOT Touch

- `backend/apps/payment/models.py` — empty, not this story's concern
- `backend/apps/payment/views.py`, `urls.py`, `tasks.py`, `serializers.py` — not this story
- `backend/core/utils.py` mask_pii / format_currency TODOs — not this story

### References

- Epic 2 Story 2.0 spec: `_bmad-output/planning-artifacts/epics.md` line 770
- Architecture phone normalization pattern: `_bmad-output/planning-artifacts/architecture.md` line 474
- Architecture enforcement rule #5: `_bmad-output/planning-artifacts/architecture.md` line 548
- Architecture app structure (payment/): `_bmad-output/planning-artifacts/architecture.md` line 651
- Error response format (INVALID_PHONE): `_bmad-output/planning-artifacts/architecture.md` line 426

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- KE prefix validation bug: initial implementation accepted 08XX/09XX/05XX (10-digit, starts-with-0 path).
  Fixed by adding `_ke_validate_significant()` — checks significant digits start with '7' or '1'.
- `__all__` in core/utils.py listed `mask_pii`/`format_currency` (F822 flake8 error); removed since they are not implemented in this story.

### Completion Notes List

- Code review (2026-03-13): 4 issues fixed (1 HIGH, 3 MEDIUM), 3 LOW items as follow-ups
  - H1 fixed: dependency inversion — implementation moved to `core/phone.py`; `apps/payment/phone.py` is now a thin re-export; `core/utils.py` imports from `core/phone.py`
  - M1 fixed: `_ke_validate_significant` now guards `not significant` before `significant[0]` — raises `PhoneNormalizationError` instead of `IndexError` on empty input
  - M2 fixed: JM and unsupported-country error path tests now assert `raw_phone` and `message` attributes
  - M3 fixed (L3): `sorted(_COUNTRY_HANDLERS)` in UNSUPPORTED_COUNTRY message — deterministic output
- `core/phone.py`: canonical implementation — `PhoneNormalizationError(ValueError)` + `normalize_phone()` with KE and JM handlers. `_COUNTRY_HANDLERS` dispatch table. Pure function — no Django imports.
- `apps/payment/phone.py`: thin re-export shim from `core/phone.py` — preserves `apps.payment.phone` import path for payment-layer code.
- `core/utils.py`: long-standing Story 1.2 TODO resolved — `normalise_mpesa_phone()` delegates to `normalize_phone(raw, country_code='KE')` via `core/phone`. `PhoneNormalizationError` re-exported.
- `apps/payment/tests/test_phone.py`: 34 parametrized pure unit tests. All pass. flake8 + black + isort clean.

### File List

**New:**
- `backend/core/phone.py`
- `backend/apps/payment/phone.py` (re-export shim)
- `backend/apps/payment/tests/test_phone.py`

**Modified:**
- `backend/core/utils.py` — implemented `normalise_mpesa_phone` (replaced TODO stub from Story 1.2); import now from `core/phone` not `apps/payment/phone`

### Change Log

- 2026-03-13: Story created for Epic 2 story 2.0
- 2026-03-13: Story implemented — all 3 tasks complete, 34 tests pass, flake8+black+isort clean
- 2026-03-13: Code review — 4 issues fixed (1 HIGH: layer inversion; 3 MEDIUM), 3 LOW follow-ups logged; status → done
