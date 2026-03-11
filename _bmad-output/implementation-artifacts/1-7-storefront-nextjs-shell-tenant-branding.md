# Story 1.7: Storefront Next.js Shell + Tenant Branding

Status: review

---

## Story

As a customer visiting any joat_stores-powered storefront,
I want to land on a fully branded page that loads the correct store's identity immediately,
So that I trust I am in the right place before I see a single product.

---

## Acceptance Criteria

**AC1 — GET /api/v1/store/branding/ (no auth, resolved by TenantMiddleware)**

Given a GET request to `/api/v1/store/branding/` with X-Store-ID header or store domain
When the response is returned
Then it includes: `store_name`, `logo_url` (WebP), `tagline`, `primary_color`, `secondary_color`, `currency`, `country`, `status`
And this endpoint requires no authentication — AllowAny

**AC2 — TenantThemeProvider injects CSS variables from branding API**

Given the storefront `app/layout.tsx` renders
When the page is server-side rendered
Then `TenantThemeProvider` injects CSS variables (`--color-primary`, `--color-secondary`, `--font-family`) from the live branding API response
And above-fold content (store name, logo, tagline) is painted on the first server-rendered frame — never a skeleton or blank white flash

**AC3 — Suspended store branded 503 page**

Given a `Store` with `status='suspended'`
When its storefront domain is visited
Then a branded 503 page is rendered SSR with the store name visible — never a generic server error

**AC4 — Persistent layout (header + footer), responsive 320px–1440px, no autoplay video**

Given the storefront base layout renders on any page
When inspected
Then it includes: persistent header (logo + store name + cart icon), main content slot, footer with plan-gated "Powered by joat stores" slot
And the layout is fully responsive from 320px to 1440px with no horizontal overflow at any breakpoint
And no autoplay video exists on any storefront page

**AC5 — Product listing shell with empty state**

Given the product listing page shell (`/`) renders
When no products exist yet
Then an empty state is shown: "Products coming soon — check back shortly." with the store logo visible
And the page structure (grid slots) is present so product cards snap in without layout shift when Story 4.1 is implemented

**AC6 — Initial payload under 200KB**

Given the storefront is accessed on a 3G connection
When the initial page load completes
Then total initial payload is under 200KB (SSR HTML + critical CSS + no blocking JS)
Enforced via: Server Components for all layout/branding content, no client-side JS imported for above-fold rendering, Tailwind v4 purge

---

## Tasks / Subtasks

- [x] **Task 1: Expand StoreSettings + StoreTheme models** (AC: 1, 2)
  - [x] `apps/store/models.py`: Add `tagline` (CharField, max_length=255, blank=True) to StoreSettings
  - [x] `apps/store/models.py`: Add `logo_url` (URLField, blank=True) to StoreSettings
  - [x] `apps/store/models.py`: Add `primary_color` (CharField, default="#1a1a1a"), `secondary_color` (default="#6b7280"), `font_family` (default="Inter") to StoreTheme
  - [x] Generate migration `0003_storesettings_storetheme_branding_fields`

- [x] **Task 2: Create BrandingSerializer + BrandingView** (AC: 1, 3)
  - [x] `apps/store/serializers.py`: BrandingSerializer — combines Store + StoreSettings + StoreTheme fields
  - [x] `apps/store/views.py`: BrandingView — `AllowAny`, uses `request.store`, returns `{data: {...}}` envelope
  - [x] Returns `status` field: `store.status` (suspended → 503 response code, plus store name in body)
  - [x] `GET_OR_CREATE` StoreSettings and StoreTheme on access — returns defaults if not yet configured

- [x] **Task 3: Wire branding URL** (AC: 1)
  - [x] `apps/store/urls.py`: add `branding/` path → BrandingView
  - [x] `config/urls.py`: include `api/v1/store/` → store URLs
  - [x] Add `api/v1/store/` to `MIDDLEWARE_BYPASS_PATHS` (branding is public, no tenant auth needed)

- [x] **Task 4: Django tests for branding API** (AC: 1, 3)
  - [x] `apps/store/tests/test_branding.py`: 10+ tests covering:
    - Returns branding fields for active store
    - Unauthenticated access allowed
    - Returns 503 status code + store name for suspended store
    - get_or_create StoreSettings + StoreTheme on first access
    - Returns correct defaults when settings/theme not configured
    - Returns 404/400 if no store resolved by middleware

- [x] **Task 5: storefront lib/branding.ts** (AC: 2)
  - [x] `storefront/src/types/branding.ts`: TypeScript interface `BrandingData`
  - [x] `storefront/src/lib/branding.ts`: `fetchTenantBranding(hostname)` — server-side fetch from `GET /api/v1/store/branding/` with `X-Store-ID` header or fallback
  - [x] Returns `BrandingData | null` on error (graceful degradation to defaults)
  - [x] Uses `process.env.NEXT_PUBLIC_API_URL` as base URL

- [x] **Task 6: Implement TenantThemeProvider + StorefrontLayout** (AC: 2, 4)
  - [x] `TenantThemeProvider.tsx`: Wire real `fetchTenantBranding()` call — inject CSS vars from live API
  - [x] If store suspended: render branded 503 inline (pass through to suspended page)
  - [x] `components/layout/StorefrontHeader.tsx`: logo (img with store name fallback) + store name + cart icon (SVG link placeholder)
  - [x] `components/layout/StorefrontFooter.tsx`: "Powered by joat stores" footer slot (always visible at this stage, plan-gated in Epic 9)
  - [x] `app/layout.tsx`: update to wrap children with StorefrontHeader + StorefrontFooter

- [x] **Task 7: Suspended store 503 page** (AC: 3)
  - [x] `app/suspended/page.tsx`: Server Component — branded 503 page, store name + "This store is currently unavailable." message
  - [x] Next.js `notFound()`-equivalent custom 503 render — HTTP 503 status via `generateMetadata` or `headers()`

- [x] **Task 8: Product listing shell + empty state** (AC: 5)
  - [x] `app/page.tsx`: Product listing shell — empty state "Products coming soon — check back shortly." with store logo
  - [x] Grid slots structure (empty divs with product-card class) so Story 4.1 cards slot in without layout shift
  - [x] Responsive grid: 1 col @ 320px, 2 col @ 640px, 3 col @ 1024px, 4 col @ 1280px

- [x] **Task 9: TypeScript + lint validation** (AC: 6)
  - [x] `tsc --noEmit` passes with 0 errors
  - [x] `eslint` passes
  - [x] No `"use client"` directive on layout/header/footer/theme-provider (Server Components only for above-fold)
  - [x] No `autoplay` attribute in any JSX

---

## Dev Notes

### API Endpoint

```
GET /api/v1/store/branding/
Authorization: not required (AllowAny)
Headers: X-Store-ID: <uuid>  OR  Host: store-domain.com (resolved by TenantMiddleware)

Response 200 (active store):
{
  "data": {
    "store_name": "Nairobi Eats",
    "logo_url": "https://..../logo.webp",  // blank string if not set
    "tagline": "Fresh food, fast delivery",
    "primary_color": "#e63946",
    "secondary_color": "#457b9d",
    "font_family": "Inter",
    "currency": "KES",
    "country": "KE",
    "status": "active"
  }
}

Response 503 (suspended store — still returns store_name for branded page):
{
  "data": {
    "store_name": "Nairobi Eats",
    "status": "suspended",
    ... (other fields as above)
  }
}
```

### CSS Variables Pattern

```css
/* Injected by TenantThemeProvider into <div style={...}> */
--color-primary: #e63946;
--color-secondary: #457b9d;
--font-family: Inter, sans-serif;
```

```tsx
/* Usage in Tailwind v4 custom utilities or inline styles */
style={{ color: 'var(--color-primary)' }}
```

### Architecture Constraints

- `TenantThemeProvider` MUST remain a Server Component (no `"use client"`)
- `fetchTenantBranding()` uses `fetch` with `cache: 'no-store'` — each SSR request gets fresh branding
- Internal SSR fetches use `NEXT_PUBLIC_API_URL` (Docker: points to Nginx)
- `logo_url` may be blank — always render store name as text fallback
- `get_or_create` pattern in `BrandingView` — never 500 on missing settings/theme
- No `autoplay` in any JSX — enforced in code review checklist (AC4 hard constraint)

### 200KB Payload Strategy

- All layout components are Server Components — zero client JS for branding/header/footer
- Tailwind v4 purges unused utilities at build time
- No CSS-in-JS libraries (styled-components, emotion) — plain Tailwind + CSS vars only
- Cart icon = SVG inline (no icon library import)
- Fonts: system font stack as fallback, custom font loaded with `next/font` (subset only)
- `next build` output with `--analyze` to verify bundle size (manual check post-story)

### File List

**New:**
- `backend/apps/store/tests/test_branding.py`
- `backend/apps/store/migrations/0003_storesettings_storetheme_branding_fields.py`
- `storefront/src/types/branding.ts`
- `storefront/src/lib/branding.ts`
- `storefront/src/components/layout/StorefrontHeader.tsx`
- `storefront/src/components/layout/StorefrontFooter.tsx`
- `storefront/src/app/suspended/page.tsx`

**Modified:**
- `backend/apps/store/models.py` — StoreSettings + StoreTheme fields
- `backend/apps/store/serializers.py` — BrandingSerializer
- `backend/apps/store/views.py` — BrandingView
- `backend/apps/store/urls.py` — branding route
- `backend/config/urls.py` — store URL include
- `backend/config/settings/base.py` — bypass path
- `storefront/src/components/layout/TenantThemeProvider.tsx` — wire branding API
- `storefront/src/app/layout.tsx` — add header/footer
- `storefront/src/app/page.tsx` — product listing shell

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Completion Notes List

- StoreSettings: added `tagline` + `logo_url`; StoreTheme: added `primary_color`, `secondary_color`, `font_family`
- Migration 0003 generated via `manage.py makemigrations store`
- BrandingSerializer: get_or_create pattern for StoreSettings + StoreTheme — never 500 on unconfigured stores
- BrandingView: AllowAny, returns `{data: {...}}` envelope, HTTP 503 for suspended stores with store_name included
- TenantMiddleware: added SUSPENDED_PASSTHROUGH_PATHS — branding endpoint bypasses middleware 503 so view can return store_name in the 503 body
- storefront_urlpatterns split from platform_urlpatterns in urls.py — both accessible from config/urls.py
- fetchTenantBranding: cache: 'no-store', graceful fallback to DEFAULT_BRANDING on any error
- TenantThemeProvider: wires real API, injects CSS vars, renders SuspendedPage inline for suspended stores
- StorefrontHeader: SVG cart icon, next/link, logo with initial-block fallback
- StorefrontFooter: "Powered by joat stores" slot, plan-gated in Epic 9
- product listing shell: empty state + responsive grid 1→2→3→4 cols
- tsc --noEmit: 0 errors | eslint: 0 errors | no `use client` in layout components | no autoplay

### Change Log

- 2026-03-11: Story created from Epic 1 story 1.7 spec

