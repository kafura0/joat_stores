# Story 1.1: Monorepo Scaffold + App Bootstrapping

Status: in-progress

---

## Story

As a platform engineer,
I want the monorepo structure and all three applications initialized from canonical templates,
so that the codebase starts from a clean, convention-compliant foundation before any Docker or infrastructure work begins.

---

## Acceptance Criteria

**AC1 — Monorepo Root Structure**

Given the monorepo root is created
When the directory structure is inspected
Then the following exist: `backend/`, `storefront/`, `admin/`, `nginx/`, `scripts/`, `docker-compose.yml`, `docker-compose.prod.yml`

**AC2 — Django Backend Scaffold**

Given `backend/` is initialized
When the Django project is bootstrapped
Then `cookiecutter-django` is used and the settings are split into `config/settings/base.py`, `config/settings/local.py`, `config/settings/production.py` — never a single `settings.py`
And `apps/` directory exists with placeholder packages for: `store`, `payment`, `product`, `order`, `restaurant`, `bar`, `contracting`, `saas`, `analytics`, `ai`, `loyalty` (plus `inventory`, `notifications` from architecture — 13 total, `users` is created by cookiecutter-django automatically)

**AC3 — Next.js Storefront Scaffold**

Given `storefront/` is initialized
When bootstrapped
Then `npx create-next-app@latest --typescript --tailwind --eslint --app` is used
And `storefront/` has a `TenantThemeProvider` shell in `components/layout/TenantThemeProvider.tsx` that reads CSS variables from hostname context — brand colours never hardcoded in components

**AC4 — Next.js Admin Scaffold**

Given `admin/` is initialized
When bootstrapped
Then `npx create-next-app@latest --typescript --tailwind --eslint --app` is used
And `admin/middleware.ts` exists as an auth guard stub

**AC5 — Preflight Script**

Given `scripts/preflight.sh` is created
When inspected
Then it checks for all required env vars (`DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `DARAJA_CONSUMER_KEY`, `DARAJA_CONSUMER_SECRET`) and exits non-zero with the missing variable name if any are absent

---

## ⚠️ Scope Boundaries — What This Story Does NOT Include

This story is **scaffolding only**. The following are explicitly out of scope and handled in subsequent stories:

| Out of scope | Handled in |
|---|---|
| Docker Compose 9-service full config | Story 1.1b |
| Redis AOF persistence config | Story 1.1b |
| Celery 5-queue wiring + DLQ | Story 1.1b |
| Nginx per-tenant routing configs | Story 1.1b |
| Store model + TenantMiddleware | Story 1.2 |
| TenantModel / TenantViewSet / TenantQuerySet base classes | Story 1.2/1.3 |
| JWT auth + RBAC | Story 1.5 |
| Storefront branding API call (TenantThemeProvider uses real API) | Story 1.7 |

Do NOT implement models, services, views, or any business logic in this story.

---

## Tasks / Subtasks

- [ ] **Task 1: Create monorepo root** (AC: 1)
  - [ ] Create top-level directories: `nginx/`, `scripts/`
  - [ ] Create empty `docker-compose.yml` stub (cookiecutter will create its own; merge in Task 2)
  - [ ] Create empty `docker-compose.prod.yml` stub
  - [ ] Create root `.gitignore` (ensure `.env`, `*.env`, `.env.*` ignored)
  - [ ] Create root `.env.example` with all canonical env vars (see Dev Notes → Environment Variables)

- [ ] **Task 2: Bootstrap Django backend with cookiecutter-django** (AC: 2)
  - [ ] Install cookiecutter: `pip install cookiecutter` (or `pipx install cookiecutter`)
  - [ ] Run cookiecutter with exact prompts (see Dev Notes → Cookiecutter Prompts)
  - [ ] Move generated project into `backend/` directory
  - [ ] Verify settings split: `config/settings/base.py`, `local.py`, `production.py` all present
  - [ ] Verify `config/settings/` does NOT contain `settings.py`
  - [ ] Add `apps/` directory to `backend/` (may need to create manually)
  - [ ] Create 13 placeholder app packages (see Dev Notes → Placeholder Apps)
  - [ ] Create `core/` placeholder directory with stub files (see Dev Notes → Core Stubs)
  - [ ] Add `requirements/` split: `base.txt`, `local.txt`, `production.txt` (verify cookiecutter created these)
  - [ ] Verify `backend/.env.example` exists and covers all backend variables

- [ ] **Task 3: Bootstrap Next.js storefront** (AC: 3)
  - [ ] Run `npx create-next-app@latest storefront --typescript --tailwind --eslint --app` from monorepo root
  - [ ] Set Node.js 24.x engine constraint in `storefront/package.json`
  - [ ] Clear default Next.js template content (remove default page content, keep structure)
  - [ ] Create `storefront/components/layout/TenantThemeProvider.tsx` (Server Component shell — see Dev Notes)
  - [ ] Update `storefront/app/layout.tsx` to import and wrap children with `TenantThemeProvider`
  - [ ] Create `storefront/lib/api.ts` stub (axios instance placeholder)
  - [ ] Create `storefront/lib/auth.ts` stub (JWT token management placeholder)
  - [ ] Create `storefront/lib/utils.ts` stub (formatCurrency, formatDate stubs)
  - [ ] Create `storefront/lib/tenant.ts` stub
  - [ ] Create `storefront/stores/cartStore.ts` stub (Zustand placeholder)
  - [ ] Create `storefront/stores/authStore.ts` stub (Zustand placeholder)
  - [ ] Create `storefront/types/index.ts` (empty typed file with a comment header)
  - [ ] Create `storefront/.env.local.example`
  - [ ] Run `npx tsc --noEmit` — must pass with zero errors

- [ ] **Task 4: Bootstrap Next.js admin** (AC: 4)
  - [ ] Run `npx create-next-app@latest admin --typescript --tailwind --eslint --app` from monorepo root
  - [ ] Set Node.js 24.x engine constraint in `admin/package.json`
  - [ ] Clear default template content
  - [ ] Create `admin/middleware.ts` stub (auth guard + role check placeholder)
  - [ ] Create `admin/lib/api.ts` stub
  - [ ] Create `admin/lib/auth.ts` stub
  - [ ] Create `admin/lib/utils.ts` stub
  - [ ] Create `admin/stores/authStore.ts` stub (Zustand placeholder)
  - [ ] Create `admin/types/index.ts`
  - [ ] Create `admin/.env.local.example`
  - [ ] Run `npx tsc --noEmit` — must pass with zero errors

- [ ] **Task 5: Create preflight script** (AC: 5)
  - [ ] Create `scripts/preflight.sh` with env var validation logic (see Dev Notes)
  - [ ] Make executable: `chmod +x scripts/preflight.sh`
  - [ ] Create `scripts/backup.sh` stub with TODO comment
  - [ ] Create `scripts/deploy.sh` stub with TODO comment
  - [ ] Test: run with one var missing → must exit 1 and print the missing var name
  - [ ] Test: run with all vars set → must exit 0

- [ ] **Task 6: Validation**
  - [ ] `cd backend && python -c "import django; print(django.__version__)"` → must print `5.2.x`
  - [ ] All placeholder app packages importable: `python -c "import apps.store, apps.product"` (no errors)
  - [ ] `cd backend && python manage.py check --settings=config.settings.local` → no errors
  - [ ] `cd storefront && npx tsc --noEmit` → zero TypeScript errors
  - [ ] `cd admin && npx tsc --noEmit` → zero TypeScript errors
  - [ ] `scripts/preflight.sh` exits 1 with missing var message when env incomplete

---

## Dev Notes

### Cookiecutter-Django Prompts (exact values)

Run from the directory where you want `backend/` to be placed (monorepo root or a temp dir):

```bash
pip install cookiecutter
cookiecutter gh:cookiecutter/cookiecutter-django
```

**Required prompt answers:**

| Prompt | Value |
|---|---|
| `project_name` | `joat_stores` |
| `project_slug` | `joat_stores` |
| `description` | Multi-tenant SaaS e-commerce for Kenyan SMEs |
| `author_name` | KAFURAHA |
| `email` | your email |
| `domain_name` | joat.com |
| `version` | 0.1.0 |
| `open_source_license` | Not open source |
| `username_type` | email |
| `timezone` | Africa/Nairobi |
| `windows` | **n** |
| `editor` | None |
| `use_docker` | **y** |
| `postgresql_version` | **17** |
| `cloud_provider` | None |
| `mail_service` | Other SMTP |
| `use_async` | **n** (Celery handles async; no ASGI complexity at MVP) |
| `use_drf` | **y** |
| `api_client` | None |
| `frontend_pipeline` | None |
| `use_celery` | **y** |
| `use_mailpit` | y (local mail testing) |
| `use_sentry` | **y** |
| `use_whitenoise` | **n** (Nginx serves static files) |
| `use_heroku` | **n** |
| `ci_tool` | **Github** |
| `keep_local_envs_in_vcs` | **n** (secrets stay out of git) |
| `debug` | y |

**After cookiecutter runs:** If it generates a nested `joat_stores/` folder, move its contents into the `backend/` folder. The final path must be `backend/manage.py`, not `joat_stores/manage.py`.

Verify the settings split immediately:
```bash
ls backend/config/settings/
# Expected: base.py  local.py  production.py
# Fail condition: any file named settings.py at any depth inside config/
```

---

### Placeholder App Packages

Create each as a proper Django app package with `__init__.py` and a minimal `apps.py`:

```bash
# From backend/ directory
cd backend
for app in store product order payment inventory restaurant bar contracting analytics notifications saas ai loyalty; do
    mkdir -p apps/$app/tests
    touch apps/$app/__init__.py
    touch apps/$app/models.py
    touch apps/$app/serializers.py
    touch apps/$app/views.py
    touch apps/$app/urls.py
    touch apps/$app/admin.py
    touch apps/$app/apps.py
    touch apps/$app/tests/__init__.py
done
```

Each `apps.py` must follow this pattern (replace `store` with actual app name):

```python
# apps/store/apps.py
from django.apps import AppConfig


class StoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.store"
```

Add all apps to `INSTALLED_APPS` in `config/settings/base.py`:
```python
LOCAL_APPS = [
    "apps.store",
    "apps.users",  # created by cookiecutter-django
    "apps.product",
    "apps.order",
    "apps.payment",
    "apps.inventory",
    "apps.restaurant",
    "apps.bar",
    "apps.contracting",
    "apps.analytics",
    "apps.notifications",
    "apps.saas",
    "apps.ai",
    "apps.loyalty",
]
```

**Note on `apps/ai/`:** Per project-context.md, the AI app needs 3 specific placeholder files:
```python
# apps/ai/services.py
"""
AI Recommendation Service

TODO: Phase 3 — Collaborative filtering implementation.
All methods return 501 Not Implemented at MVP.
"""


class RecommendationService:
    """Placeholder. Phase 3 implementation."""

    def get_recommendations(self, store_id: int, customer_id: int) -> list:
        raise NotImplementedError("Phase 3: AI recommendations not yet implemented.")
```

```python
# apps/ai/models.py
"""
AI Event capture model.

AIEvent is append-only. Captures product views, cart events, searches, and order
completions from day one so historical data exists when Phase 3 ships.
All fields are stubs — Epic 11 adds the full model.
"""
# TODO: Epic 11 — implement full AIEvent model
```

```python
# apps/ai/views.py
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class AIRecommendationsView(APIView):
    """Placeholder. Returns 501 until Phase 3 AI engine is implemented."""

    def get(self, request):
        return Response(
            {"errors": [{"field": None, "message": "AI recommendations not yet available.", "code": "NOT_IMPLEMENTED"}]},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )
```

---

### Core Directory Stubs

Create `backend/core/` with placeholder files. These will be fully implemented in Stories 1.2 and 1.3 — do NOT implement logic here, only stubs with docstrings:

```
backend/core/
├── __init__.py
├── models.py          # TenantModel, SoftDeleteModel — stub
├── querysets.py       # TenantQuerySet — stub
├── permissions.py     # IsStoreScoped, IsPlatformAdmin, IsStoreOwner, IsStoreManager — stubs
├── serializers.py     # TenantSerializer — stub
├── views.py           # TenantViewSet — stub
├── middleware.py      # TenantMiddleware — stub
├── exceptions.py      # custom_exception_handler — stub
├── pagination.py      # StoreCursorPagination — stub
└── utils.py           # normalise_mpesa_phone, format_currency, mask_pii — stubs
```

Each stub file should have a docstring explaining what it will contain, e.g.:

```python
# core/middleware.py
"""
TenantMiddleware

Resolves request.store from:
  1. Hostname (Host header): matches Store.domain
  2. X-Store-ID header: matches Store.id

Sets request.store before any view logic runs.
Returns HTTP 404 if no matching store found.
Returns HTTP 503 if store.status == 'suspended'.

Skips resolution for platform subdomains (admin.joat.com, api.joat.com).

Implementation: Story 1.2
"""
# TODO: Story 1.2 — implement TenantMiddleware
```

---

### TenantThemeProvider Shell

This is the **most architecture-critical shell in Story 1.1**. It establishes the pattern that all subsequent storefront stories must follow: CSS variables, never hardcoded colors.

```tsx
// storefront/components/layout/TenantThemeProvider.tsx
// Server Component (no 'use client' — reads hostname server-side)

import { headers } from "next/headers";
import React from "react";

interface TenantTheme {
  primaryColor: string;
  secondaryColor: string;
  fontFamily: string;
}

// Default theme used until Story 1.7 wires the real branding API
const DEFAULT_THEME: TenantTheme = {
  primaryColor: "#1a1a1a",
  secondaryColor: "#6b7280",
  fontFamily: "Inter, sans-serif",
};

/**
 * TenantThemeProvider
 *
 * Injects CSS variables from the tenant's branding configuration.
 * Story 1.7 adds the real branding API call (GET /api/v1/store/branding/).
 * At this stage, it injects default theme variables only.
 *
 * CSS variables injected:
 *   --color-primary    → brand primary colour
 *   --color-secondary  → brand secondary colour
 *   --font-family      → brand font (defaults to Inter)
 *
 * RULE: Brand colours must NEVER be hardcoded in component files.
 * Always use var(--color-primary) in Tailwind or inline styles.
 */
export default async function TenantThemeProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  // TODO: Story 1.7 — fetch branding from GET /api/v1/store/branding/
  // const headersList = await headers();
  // const hostname = headersList.get("host") ?? "";
  // const branding = await fetchTenantBranding(hostname);
  const theme = DEFAULT_THEME;

  const cssVariables = {
    "--color-primary": theme.primaryColor,
    "--color-secondary": theme.secondaryColor,
    "--font-family": theme.fontFamily,
  } as React.CSSProperties;

  return (
    <div style={cssVariables} className="min-h-screen">
      {children}
    </div>
  );
}
```

Update `storefront/app/layout.tsx`:
```tsx
// storefront/app/layout.tsx
import type { Metadata } from "next";
import TenantThemeProvider from "@/components/layout/TenantThemeProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: "joat_stores",
  description: "Your store",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <TenantThemeProvider>{children}</TenantThemeProvider>
      </body>
    </html>
  );
}
```

**Critical pattern rules for TenantThemeProvider:**
- MUST be a Server Component (no `'use client'`) — reads hostname server-side via Next.js `headers()`
- Never add `'use client'` to `layout.tsx` or `TenantThemeProvider` — doing so makes every child a Client Component
- CSS variables injected as inline style on root div — consumed via `var(--color-primary)` in all components
- Story 1.7 wires the real branding API; this story establishes the pattern only

---

### Admin middleware.ts Stub

```typescript
// admin/middleware.ts
// Auth guard and role-based access control for admin routes.
// Full implementation in Story 1.8.
// At this stage: stub that passes all requests through.

import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Admin middleware
 *
 * Story 1.8 implements:
 * - JWT token validation from memory / httpOnly cookie
 * - Role check: platform_admin → /platform/, store_owner/store_manager → /dashboard/
 * - Redirect unauthenticated users to /login
 *
 * RULE: Never use next-auth — conflicts with custom store_id JWT claim.
 * Auth is custom via lib/auth.ts using httpOnly cookie for refresh token.
 */
export function middleware(request: NextRequest) {
  // TODO: Story 1.8 — implement JWT auth guard
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!login|_next/static|_next/image|favicon.ico).*)"],
};
```

---

### Lib Stubs

**storefront/lib/api.ts** and **admin/lib/api.ts** (identical stubs):
```typescript
// lib/api.ts
// axios instance with auth interceptor.
// Full implementation in Story 1.5 (JWT) and Story 1.8 (admin auth).

import axios from "axios";

/**
 * API client
 *
 * RULE: ALL HTTP requests must go through this instance — never use fetch() directly.
 * This instance will add:
 *   - Authorization: Bearer <access_token> header (from memory)
 *   - Automatic token refresh on 401 using httpOnly refresh cookie
 *   - {data, meta, errors} response envelope parsing
 *
 * Story 1.5 wires the auth interceptor.
 */
export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

// TODO: Story 1.5 — add auth interceptor (request + response)
// TODO: Story 1.5 — add 401 → token refresh → retry logic
```

**storefront/lib/utils.ts** and **admin/lib/utils.ts**:
```typescript
// lib/utils.ts
// Shared formatting utilities.
// RULE: Always use these — never format currency or dates inline in components.

/**
 * Format a monetary amount in KES.
 * @param amount - string decimal e.g. "1500.00"
 * @returns formatted string e.g. "KES 1,500"
 */
export function formatCurrency(amount: string): string {
  // TODO: implement proper KES formatting with Intl.NumberFormat
  return `KES ${parseFloat(amount).toLocaleString("en-KE")}`;
}

/**
 * Format a UTC ISO datetime string in Africa/Nairobi timezone.
 * @param isoString - ISO 8601 UTC string e.g. "2026-02-24T12:00:00Z"
 * @returns formatted string in East Africa Time
 */
export function formatDate(isoString: string): string {
  // TODO: implement with Intl.DateTimeFormat { timeZone: 'Africa/Nairobi' }
  return new Date(isoString).toLocaleString("en-KE", {
    timeZone: "Africa/Nairobi",
  });
}
```

**storefront/lib/tenant.ts**:
```typescript
// storefront/lib/tenant.ts
// Tenant resolution utilities for the storefront.
// Full implementation in Story 1.7.

/**
 * Resolves the store identifier from the current hostname.
 * Used by TenantThemeProvider and storefront middleware.
 * Story 1.7 adds the branding API call.
 */
export function getTenantFromHostname(hostname: string): string {
  // TODO: Story 1.7 — resolve tenant slug from hostname
  return hostname.split(".")[0] ?? "default";
}
```

**storefront/types/index.ts** and **admin/types/index.ts**:
```typescript
// types/index.ts
// Shared TypeScript type definitions.
// RULE: All types live here — never define types inline in component files.
// RULE: Interfaces prefixed I (IProduct, IOrder); plain types PascalCase (OrderStatus).

// Placeholder — types added as domain stories are implemented.

export type TenantType = "retail" | "restaurant" | "bar" | "contracting";

export type OrderStatus =
  | "pending"
  | "confirmed"
  | "fulfilled"
  | "completed"
  | "cancelled";

export interface IApiResponse<T> {
  data: T;
}

export interface IApiListResponse<T> {
  data: T[];
  meta: {
    count: number;
    next: string | null;
    previous: string | null;
  };
}

export interface IApiError {
  field: string | null;
  message: string;
  code: string;
}

export interface IApiErrorResponse {
  errors: IApiError[];
}
```

---

### Zustand Store Stubs

**storefront/stores/cartStore.ts**:
```typescript
// storefront/stores/cartStore.ts
// Cart state management.
// Full implementation in Story 4.1 (Retail Cart).

import { create } from "zustand";

interface CartStore {
  // TODO: Story 4.1 — add cart items, totals, open/close state
  isOpen: boolean;
  setOpen: (open: boolean) => void;
}

export const useCartStore = create<CartStore>((set) => ({
  isOpen: false,
  setOpen: (open) => set({ isOpen: open }),
}));
```

**storefront/stores/authStore.ts** and **admin/stores/authStore.ts**:
```typescript
// stores/authStore.ts
// Auth state management.
// Full implementation in Story 1.5 (JWT) and Story 1.8 (admin).
// RULE: JWT access token stored in memory only — never localStorage.

import { create } from "zustand";

interface AuthStore {
  // Access token in memory only — never localStorage
  accessToken: string | null;
  setAccessToken: (token: string | null) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  accessToken: null,
  setAccessToken: (token) => set({ accessToken: token }),
  clearAuth: () => set({ accessToken: null }),
}));
```

---

### Preflight Script

```bash
#!/usr/bin/env bash
# scripts/preflight.sh
# Pre-flight environment check.
# Run before EVERY `docker compose up` — including up --build, up -d, and single-service restarts.
# Exits non-zero with the name of the first missing variable if any are absent.
#
# Usage: ./scripts/preflight.sh
# Returns: 0 if all checks pass, 1 if any check fails

set -euo pipefail

REQUIRED_VARS=(
  "DATABASE_URL"
  "REDIS_URL"
  "SECRET_KEY"
  "DARAJA_CONSUMER_KEY"
  "DARAJA_CONSUMER_SECRET"
)

echo "==> joat_stores pre-flight check"

FAILED=0

for var in "${REQUIRED_VARS[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    echo "❌ MISSING: $var is not set"
    FAILED=1
  else
    echo "✓ $var"
  fi
done

if [[ $FAILED -eq 1 ]]; then
  echo ""
  echo "Pre-flight FAILED. Set all missing environment variables and retry."
  exit 1
fi

echo ""
echo "✅ Pre-flight passed. All required environment variables are set."
exit 0
```

**Note:** Load your `.env` file before running:
```bash
set -a && source backend/.env && set +a && ./scripts/preflight.sh
```

---

### Environment Variables (`.env.example` at monorepo root)

```bash
# .env.example — Canonical env var reference for joat_stores
# Copy to backend/.env (never commit the actual .env file)

# --- Django ---
DJANGO_SECRET_KEY=your-secret-key-here-minimum-50-chars
DJANGO_SETTINGS_MODULE=config.settings.local
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# --- Database ---
DATABASE_URL=postgres://joat_stores:password@postgres:5432/joat_stores

# --- Redis ---
REDIS_URL=redis://redis:6379/0

# --- M-Pesa / Daraja (use sandbox credentials until business registration complete) ---
DARAJA_CONSUMER_KEY=your-sandbox-consumer-key
DARAJA_CONSUMER_SECRET=your-sandbox-consumer-secret
DARAJA_SHORTCODE=174379
DARAJA_PASSKEY=your-sandbox-passkey
DARAJA_ENV=sandbox
# Swap DARAJA_ENV=production + update key/secret/shortcode/passkey to go live; no code change needed

# --- Email (Other SMTP for MVP) ---
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-email-password
EMAIL_USE_TLS=True

# --- Sentry ---
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id

# --- Celery ---
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# --- Next.js (storefront) ---
# NEXT_PUBLIC_API_URL=http://localhost/api/v1

# --- Next.js (admin) ---
# NEXT_PUBLIC_API_URL=http://localhost/api/v1
```

---

### Node.js Version Requirement

**Node.js 24.x LTS is required.** Node.js 20.x reaches End-of-Life on April 30, 2026 — do not use it.

Add to both `storefront/package.json` and `admin/package.json`:

```json
{
  "engines": {
    "node": ">=24.0.0",
    "npm": ">=10.0.0"
  }
}
```

Add `.nvmrc` to both `storefront/` and `admin/`:
```
24
```

The Next.js version should be `^16.1.0` (16.1 is the current stable; 16.0 is superseded).

---

### Python Dependencies (backend/requirements/base.txt additions)

After cookiecutter runs, verify or add these to `requirements/base.txt`:

```
# Core
Django==5.2.*
djangorestframework==3.16.*
djangorestframework-simplejwt==5.4.*
django-allauth[socialaccount]==65.*
django-cors-headers==4.*
django-environ==0.11.*

# Tenant / Security
django-safedelete==1.4.*
django-encrypted-fields==0.2.*
django-filter==24.*

# Async
celery==5.6.2
redis==5.*
django-celery-beat==2.7.*

# API schema
drf-spectacular==0.28.*

# Logging / Monitoring
structlog==24.*
sentry-sdk[django]==2.*

# Media
Pillow==11.*

# Utilities
psycopg2-binary==2.9.*
```

`requirements/local.txt` additions:
```
pytest==8.*
pytest-django==4.*
factory-boy==3.*
pytest-cov==6.*
django-debug-toolbar==4.*
mailpit  # local email testing (cookiecutter adds this)
```

`requirements/production.txt` additions:
```
gunicorn==23.*
```

---

### Project Structure Notes

**Final monorepo structure after this story:**

```
joat_stores/                     ← monorepo root
├── .github/
│   └── workflows/               ← empty dir; Story 12.1 adds ci.yml + deploy.yml
├── backend/                     ← cookiecutter-django output
│   ├── manage.py
│   ├── Dockerfile               ← generated by cookiecutter
│   ├── requirements/
│   │   ├── base.txt
│   │   ├── local.txt
│   │   └── production.txt
│   ├── config/
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   ├── local.py
│   │   │   └── production.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── celery.py
│   ├── core/                    ← stub files; implemented in Stories 1.2-1.3
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── querysets.py
│   │   ├── permissions.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── middleware.py
│   │   ├── exceptions.py
│   │   ├── pagination.py
│   │   └── utils.py
│   └── apps/
│       ├── users/               ← created by cookiecutter-django
│       ├── store/               ← placeholder; Story 1.2
│       ├── product/             ← placeholder; Story 4.1
│       ├── order/               ← placeholder; Story 4.3
│       ├── payment/             ← placeholder; Epic 2
│       ├── inventory/           ← placeholder; Story 4.6
│       ├── restaurant/          ← placeholder; Epic 3
│       ├── bar/                 ← placeholder; Epic 5
│       ├── contracting/         ← placeholder; Epic 6
│       ├── analytics/           ← placeholder; Epic 8
│       ├── notifications/       ← placeholder; Epic 7
│       ├── saas/                ← placeholder (stub Plan+StoreSubscription in Story 1.4)
│       ├── ai/                  ← placeholder with 501 views; Epic 11
│       └── loyalty/             ← placeholder; Epic 10
├── storefront/                  ← Next.js 16.1
│   ├── app/
│   │   ├── layout.tsx           ← wraps TenantThemeProvider
│   │   ├── page.tsx             ← cleared template content
│   │   └── globals.css
│   ├── components/
│   │   └── layout/
│   │       └── TenantThemeProvider.tsx  ← KEY SHELL; see Dev Notes
│   ├── lib/
│   │   ├── api.ts               ← stub
│   │   ├── auth.ts              ← stub
│   │   ├── tenant.ts            ← stub
│   │   └── utils.ts             ← stub
│   ├── stores/
│   │   ├── cartStore.ts         ← stub
│   │   └── authStore.ts         ← stub
│   ├── types/
│   │   └── index.ts             ← base types
│   ├── .env.local.example
│   ├── .nvmrc                   ← "24"
│   └── package.json             ← engines: node >=24
├── admin/                       ← Next.js 16.1
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── globals.css
│   ├── middleware.ts             ← auth guard stub
│   ├── lib/
│   │   ├── api.ts               ← stub
│   │   ├── auth.ts              ← stub
│   │   └── utils.ts             ← stub
│   ├── stores/
│   │   └── authStore.ts         ← stub
│   ├── types/
│   │   └── index.ts
│   ├── .env.local.example
│   ├── .nvmrc                   ← "24"
│   └── package.json             ← engines: node >=24
├── nginx/                       ← empty dir; Story 1.1b adds configs
│   └── .gitkeep
├── scripts/
│   ├── preflight.sh             ← ✅ implemented this story
│   ├── backup.sh                ← stub (TODO: Story 12.2)
│   └── deploy.sh                ← stub (TODO: Story 12.1)
├── docker-compose.yml           ← cookiecutter stub; Story 1.1b replaces
├── docker-compose.prod.yml      ← empty stub; Story 1.1b fills
├── .env.example                 ← canonical env var reference
├── .gitignore                   ← MUST include .env, *.env, .env.*
└── README.md                    ← optional
```

**Naming compliance check (must pass before marking story complete):**
- No file named `settings.py` anywhere in `backend/config/` — only `base.py`, `local.py`, `production.py`
- All app directories are `snake_case` singular: `store`, `product`, `order` (never `stores`, `products`)
- `core/` is not inside `apps/` — it's at `backend/core/`

---

### Testing for Story 1.1

**Backend tests (no business logic yet — scaffold validation only):**

```bash
# 1. Python + Django setup check
cd backend
python -c "import django; print(django.__version__)"
# Expected: 5.2.x

# 2. All placeholder apps importable
python -c "
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()
import apps.store, apps.product, apps.order, apps.payment
import apps.restaurant, apps.bar, apps.contracting
import apps.analytics, apps.notifications, apps.saas, apps.ai, apps.loyalty
import apps.inventory
print('All apps importable OK')
"

# 3. Django system check (must be clean)
python manage.py check --settings=config.settings.local

# 4. Pytest collection (no tests yet, but collection must not error)
pytest --co -q
```

**Frontend TypeScript checks:**

```bash
# Storefront — zero errors required
cd storefront && npx tsc --noEmit

# Admin — zero errors required
cd admin && npx tsc --noEmit
```

**Preflight script tests:**

```bash
# Test 1: Fails when vars absent (expected: exit 1)
./scripts/preflight.sh
echo "Exit code: $?"  # Expected: 1

# Test 2: Passes when all vars set (expected: exit 0)
DATABASE_URL="postgres://x" \
REDIS_URL="redis://x" \
SECRET_KEY="test-secret-key-that-is-long-enough-to-pass-validation" \
DARAJA_CONSUMER_KEY="test" \
DARAJA_CONSUMER_SECRET="test" \
./scripts/preflight.sh
echo "Exit code: $?"  # Expected: 0
```

---

### Critical Anti-Patterns — Do NOT Do These

1. **Never create a `settings.py`** — settings MUST be split into `base.py`, `local.py`, `production.py` from day one; cookiecutter-django does this correctly
2. **Never add `'use client'` to `TenantThemeProvider.tsx` or `layout.tsx`** — makes all children Client Components, destroying SSR and performance
3. **Never install `next-auth`** — conflicts with custom `store_id` JWT claim; custom auth via `lib/auth.ts` only
4. **Never hardcode brand colours in any component** — always `var(--color-primary)` via CSS variables from TenantThemeProvider
5. **Never use `float` for money types** — Django: `DecimalField(max_digits=10, decimal_places=2)`; Python: `Decimal`; TS: `string`
6. **Never commit `.env` files** — `.gitignore` must exclude `*.env`, `.env`, `.env.*` from day one
7. **Never use `models.Model` directly in any app model** — always `TenantModel`; this story creates stubs only, so no models yet — just ensure the pattern is documented in stub comments
8. **Never create `apps/core/`** — `core/` lives at `backend/core/`, not inside `apps/`; this is a frequently made mistake

---

### Architecture References

- [Source: architecture.md#Starter Template Evaluation] — cookiecutter-django bootstrap procedure
- [Source: architecture.md#Complete Project Directory Structure] — canonical monorepo layout
- [Source: architecture.md#Django Backend Organisation] — apps structure and core/ placement
- [Source: architecture.md#Frontend Architecture] — TenantThemeProvider pattern, Server Components default
- [Source: architecture.md#Next.js Frontend Organisation] — storefront and admin directory structure
- [Source: architecture.md#Enforcement Guidelines] — 10 mandatory rules for all AI agents
- [Source: project-context.md#AI Scaffold] — ai/ app requirements (501 endpoints, AIEvent stub)
- [Source: project-context.md#Common Misinterpretations] — 'use client' inheritance warning
- [Source: epics.md#Story 1.1] — acceptance criteria (canonical)

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None at story creation._

### Completion Notes List

_To be filled by the dev agent after implementation._

### File List

_To be confirmed by dev agent after implementation. Expected files (not exhaustive):_

**New files — Backend:**
- `backend/core/__init__.py`
- `backend/core/models.py`
- `backend/core/querysets.py`
- `backend/core/permissions.py`
- `backend/core/serializers.py`
- `backend/core/views.py`
- `backend/core/middleware.py`
- `backend/core/exceptions.py`
- `backend/core/pagination.py`
- `backend/core/utils.py`
- `backend/apps/store/__init__.py` (+ models, serializers, views, urls, admin, apps, tests/)
- `backend/apps/product/` (same structure)
- `backend/apps/order/` (same structure)
- `backend/apps/payment/` (same structure)
- `backend/apps/inventory/` (same structure)
- `backend/apps/restaurant/` (same structure)
- `backend/apps/bar/` (same structure)
- `backend/apps/contracting/` (same structure)
- `backend/apps/analytics/` (same structure)
- `backend/apps/notifications/` (same structure)
- `backend/apps/saas/` (same structure)
- `backend/apps/ai/__init__.py`, `models.py`, `services.py`, `views.py`, `urls.py`
- `backend/apps/loyalty/` (same structure)
- `backend/.env.example`

**New files — Storefront:**
- `storefront/components/layout/TenantThemeProvider.tsx`
- `storefront/app/layout.tsx` (modified from template)
- `storefront/lib/api.ts`
- `storefront/lib/auth.ts`
- `storefront/lib/tenant.ts`
- `storefront/lib/utils.ts`
- `storefront/stores/cartStore.ts`
- `storefront/stores/authStore.ts`
- `storefront/types/index.ts`
- `storefront/.env.local.example`
- `storefront/.nvmrc`

**New files — Admin:**
- `admin/middleware.ts`
- `admin/lib/api.ts`
- `admin/lib/auth.ts`
- `admin/lib/utils.ts`
- `admin/stores/authStore.ts`
- `admin/types/index.ts`
- `admin/.env.local.example`
- `admin/.nvmrc`

**New files — Root:**
- `scripts/preflight.sh` (chmod +x)
- `scripts/backup.sh` (stub)
- `scripts/deploy.sh` (stub)
- `.env.example`
- `nginx/.gitkeep`
- `docker-compose.yml` (cookiecutter stub — Story 1.1b replaces)
- `docker-compose.prod.yml` (empty stub)
