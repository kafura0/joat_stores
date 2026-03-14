# Story 1.8: Admin Next.js Shell + Authenticated Layout

Status: done

---

## Story

As a store owner, store manager, or platform admin,
I want a secure login page and a role-aware admin shell that I land in immediately after authentication,
So that I can access my tools without friction and without ever seeing another tenant's navigation.

---

## Acceptance Criteria

**AC1 — Unauthenticated redirect to /login**

Given an unauthenticated user visits any admin route
When the request is processed
Then they are redirected to `/login` immediately — no admin content is rendered or leaked

**AC2 — Login flow: token + role redirect**

Given the login page at `/login` renders
When a store staff member submits valid credentials
Then `POST /api/v1/auth/token/` is called, the access token is stored in memory (never `localStorage`), and the `httpOnly` refresh token cookie is set
And the user is redirected to the dashboard appropriate for their role: `platform_admin` → `/platform/`, `store_owner` / `store_manager` → `/dashboard/`

**AC3 — Invalid credentials error**

Given invalid credentials are submitted
When the login request returns HTTP 401
Then the error message is: "Incorrect email or password." — no indication of whether the email exists (prevents enumeration)

**AC4 — Store-scoped admin shell navigation**

Given an authenticated `store_owner` or `store_manager` views the admin shell
When the layout renders
Then the sidebar shows only store-scoped navigation items: Dashboard, Orders, Products, Customers, Analytics, Settings
And the header displays the store name and a Logout button

**AC5 — Platform admin shell navigation**

Given an authenticated `platform_admin` views the admin shell
When the layout renders
Then the sidebar shows platform-scoped navigation: Stores, Analytics, Plans, System Health
And no store-specific items appear — platform admin has no store context

**AC6 — Logout**

Given the Logout button is tapped
When clicked
Then `POST /api/v1/auth/logout-all/` is called, the access token is cleared from memory, the refresh cookie is cleared, and the user is redirected to `/login`

**AC7 — Silent token refresh on 401**

Given an API call returns HTTP 401 (expired access token)
When detected by the frontend API client
Then `POST /api/v1/auth/token/refresh/` is called automatically using the refresh cookie
And if refresh also fails (cookie expired or revoked), the user is redirected to `/login` with session expiry message

**AC8 — Mobile-responsive layout (320px+, 48px tap targets)**

Given the admin shell loads on a budget Android device
When rendered
Then all sidebar navigation items have minimum 48×48px tap targets
And the layout is usable at 320px width — sidebar collapses to a hamburger menu on mobile

---

## Tasks / Subtasks

- [x] **Task 1: Auth types + expanded auth store** (AC: 2, 4, 5)
  - [x] `admin/src/types/auth.ts`: `UserRole`, `IUser` (id, email, role, store_id), `ITokenResponse`, `ILoginCredentials`
  - [x] `admin/src/stores/authStore.ts`: expand — add `user: IUser | null`, `setUser`, actions; keep `accessToken` in memory only

- [x] **Task 2: lib/auth.ts — token helpers** (AC: 2, 6, 7)
  - [x] `decodeToken(token)` — base64 decode JWT payload (no library), return `{user_id, role, store_id, exp}`
  - [x] `isTokenExpired(token)` — check exp vs Date.now()
  - [x] `performLogin(email, password)` — POST /api/v1/auth/token/, store access token + decoded user in authStore, return role
  - [x] `performLogout()` — POST /api/v1/auth/logout-all/ (best-effort), clear authStore
  - [x] `performRefresh()` — POST /api/v1/auth/token/refresh/, update accessToken in authStore, return new token or null on failure

- [x] **Task 3: lib/api.ts — auth interceptors** (AC: 7)
  - [x] Request interceptor: attach `Authorization: Bearer <accessToken>` from authStore
  - [x] Response interceptor: on 401 → refresh → retry once with new token; queue parallel requests during refresh
  - [x] On refresh failure: clear auth, redirect `window.location.href = '/login?expired=1'`

- [x] **Task 4: Next.js middleware — route guard** (AC: 1)
  - [x] `admin/middleware.ts`: check `auth_session` presence cookie (client-set on login/cleared on logout)
  - [x] No cookie + path not `/login` → redirect to `/login`
  - [x] Note: httpOnly `refresh_token` cookie is path-restricted to `/api/v1/auth/` so unavailable in edge middleware; `auth_session` is a non-sensitive UX guard (security enforced by backend)
  - [x] matcher excludes `/_next/static`, `/_next/image`, `favicon.ico`

- [x] **Task 5: Login page** (AC: 2, 3)
  - [x] `admin/src/app/login/page.tsx` — Client Component (`"use client"`)
  - [x] Email + password form; submit calls `performLogin()`
  - [x] On success: redirect to `/platform/` for `platform_admin`, else `/dashboard/`
  - [x] On 401: display "Incorrect email or password." — no email-exists hint
  - [x] Loading state during submission (disabled button, "Signing in…" text)
  - [x] If `?expired=1` query param: display "Your session has expired. Please log in again."

- [x] **Task 6: Authenticated layout + AdminShell** (AC: 4, 5, 8)
  - [x] `admin/src/app/(admin)/layout.tsx` — Client Component; on mount: if no accessToken → `performRefresh()`; if fails → `/login`
  - [x] `admin/src/components/layout/AdminSidebar.tsx` — role-aware sidebar with mobile hamburger, min 48×48px tap targets
  - [x] `admin/src/components/layout/AdminHeader.tsx` — store name label + Logout button

- [x] **Task 7: Route page stubs** (AC: 2, 4, 5)
  - [x] `admin/src/app/(admin)/dashboard/page.tsx` — stub for store role
  - [x] `admin/src/app/(admin)/platform/page.tsx` — stub for platform admin
  - [x] `admin/src/app/page.tsx` — root redirect: role-based or → /login

- [x] **Task 8: TypeScript + lint validation** (AC: all)
  - [x] `tsc --noEmit` passes with 0 errors
  - [x] `eslint` passes with 0 errors (--max-warnings=0)
  - [x] No access token written to `localStorage` or `sessionStorage` (verified via grep)

### Review Follow-ups (AI)

- [ ] [AI-Review][LOW] Add `aria-expanded` to hamburger button and update `aria-label` dynamically (`AdminHeader.tsx:33`)
- [ ] [AI-Review][LOW] Add `Secure` flag to `auth_session` cookie in production environments (`lib/auth.ts:23`)
- [ ] [AI-Review][LOW] Reset `isRefreshing = false` in a logout hook to prevent indefinitely queued requests if logout fires mid-refresh (`lib/api.ts:42`)

---

## Dev Notes

### Auth Architecture

```
Login flow:
  1. POST /api/v1/auth/token/ → { data: { access, role, store_id } }
  2. access token → authStore (memory only, never localStorage)
  3. refresh token → httpOnly cookie (set by backend, path=/api/v1/auth/)
  4. role/store_id → decoded from JWT payload via decodeToken()
  5. redirect based on role

Route guard (middleware.ts):
  - Runs on Next.js edge runtime
  - Cannot access Zustand store (in-memory)
  - Uses refresh_token httpOnly cookie as proxy for "logged in"
  - Fine-grained role routing happens client-side in (admin)/layout.tsx

Token refresh:
  - 401 response → interceptor calls POST /api/v1/auth/token/refresh/
  - Backend reads refresh cookie automatically (same-origin)
  - New access token returned in body → update authStore
  - Original request retried once
  - Refresh failure → logout + /login?expired=1
```

### JWT Payload

```typescript
// Decoded from access token base64 payload (no jwt library needed)
{
  user_id: string,      // UUID
  role: "platform_admin" | "store_owner" | "store_manager" | "customer",
  store_id: string | null,  // null for platform_admin
  exp: number,          // Unix timestamp
  iat: number,
  token_type: "access"
}
```

### API Response Shape

```typescript
// POST /api/v1/auth/token/ — 200
{ data: { access: string, role: string, store_id: string | null } }

// POST /api/v1/auth/token/ — 401
{ errors: [{ field: null, message: "Invalid credentials.", code: "INVALID_CREDENTIALS" }] }

// POST /api/v1/auth/token/refresh/ — 200
{ data: { access: string } }

// POST /api/v1/auth/logout-all/ — 200
{ data: { message: "All sessions invalidated." } }
```

### Admin App Structure (target)

```
admin/src/
  app/
    layout.tsx              — root layout (no auth check here)
    page.tsx                — root redirect (client-side role routing)
    login/
      page.tsx              — login form (Client Component)
    (admin)/
      layout.tsx            — authenticated layout (Client Component, token refresh on mount)
      dashboard/
        page.tsx            — store owner/manager dashboard shell
      platform/
        page.tsx            — platform admin shell
  components/layout/
    AdminSidebar.tsx        — role-aware sidebar
    AdminHeader.tsx         — header with store name + logout
  lib/
    auth.ts                 — login, logout, refresh, decodeToken
    api.ts                  — axios instance + auth interceptors
  stores/
    authStore.ts            — Zustand in-memory auth state
  types/
    auth.ts                 — auth-specific types
    index.ts                — existing shared types (do not break)
```

### Architecture Constraints

- NEVER use `next-auth` — conflicts with custom `store_id` JWT claim
- NEVER store access token in `localStorage` or `sessionStorage`
- Middleware runs on edge runtime — cannot import Zustand or Node.js-only modules
- Admin app uses `axios` (already in package.json) not `fetch` for API calls
- Tailwind v4 for styling — consistent with storefront

### Existing Files to Modify

- `admin/middleware.ts` — replace stub with real auth guard
- `admin/src/app/layout.tsx` — update metadata + remove unused Geist fonts if not needed
- `admin/src/app/page.tsx` — replace empty stub with role-based redirect
- `admin/src/lib/auth.ts` — replace stub with full implementation
- `admin/src/lib/api.ts` — replace stub with auth interceptors
- `admin/src/stores/authStore.ts` — expand with user info + actions
- `admin/src/types/index.ts` — do not modify (existing types remain)

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Completion Notes List

- Code review (2026-03-13): 6 issues fixed (2 HIGH, 4 MEDIUM), 3 LOW items created as follow-ups
  - H1 fixed: AdminSidebar active-route bleeding — more-specific nav item wins over prefix match
  - H2 fixed: AdminHeader store name — `IUser.store_name?` field added; shows "My Store" stub pending Epic 4 store detail API
  - M1 fixed: login catch now distinguishes 401 (credentials error) from other errors (generic message)
  - M2 fixed: performRefresh uses `payload.email ?? ""` not hardcoded `""`
  - M3 fixed: `auth_session` cookie gets `Max-Age=604800` (7 days) — survives browser restart
  - M4 fixed: performLogin throws on null payload instead of silently using `id: ""`
- Auth types in `types/auth.ts`: UserRole, IUser, ITokenResponse, ILoginCredentials, IJWTPayload
- AuthStore expanded: user + accessToken in memory, clearAuth, isAuthenticated(), getRole() helpers
- lib/auth.ts: decodeToken (base64url decode, no jwt lib), isTokenExpired, performLogin (POST /auth/token/), performLogout (best-effort + local clear), performRefresh (POST /auth/token/refresh/)
- auth_session presence cookie: non-sensitive UX indicator set on login, cleared on logout — enables middleware redirect without exposing the httpOnly refresh_token (which is path-restricted to /api/v1/auth/)
- lib/api.ts: axios instance with request interceptor (Bearer token) + response interceptor (401 → refresh → retry once, queue parallel requests during in-flight refresh)
- middleware.ts: checks auth_session cookie, redirects unauthenticated to /login; matcher excludes static assets
- login/page.tsx: email+password form, performLogin(), role-based redirect, AC3 error message, ?expired=1 session expiry notice, Suspense wrapper for useSearchParams
- (admin)/layout.tsx: Client Component, on-mount refresh hydration, AdminHeader + AdminSidebar + children
- AdminSidebar: role-aware nav (STORE_NAV vs PLATFORM_NAV), mobile off-canvas drawer with overlay, min 48×48px tap targets, active route highlight
- AdminHeader: hamburger (mobile), store name label, Logout button → performLogout() + router.push('/login')
- Route stubs: /dashboard/ (store), /platform/ (platform_admin), root page.tsx (role-based redirect)
- app/layout.tsx: stripped default Geist boilerplate, updated metadata
- tsc: 0 errors | eslint: 0 warnings/errors | no localStorage usage

### File List

**New:**
- `admin/src/types/auth.ts`
- `admin/src/app/login/page.tsx`
- `admin/src/app/(admin)/layout.tsx`
- `admin/src/app/(admin)/dashboard/page.tsx`
- `admin/src/app/(admin)/platform/page.tsx`
- `admin/src/components/layout/AdminSidebar.tsx`
- `admin/src/components/layout/AdminHeader.tsx`

**Modified:**
- `admin/src/stores/authStore.ts` — expanded with user info + actions
- `admin/src/lib/auth.ts` — full implementation (was stub)
- `admin/src/lib/api.ts` — auth interceptors (was stub)
- `admin/middleware.ts` — real auth guard (was pass-through stub)
- `admin/src/app/layout.tsx` — cleaned metadata, stripped Geist boilerplate
- `admin/src/app/page.tsx` — role-based redirect (was empty stub)

### Change Log

- 2026-03-11: Story created for Epic 1 story 1.8
- 2026-03-11: Story implemented — all 8 tasks complete, tsc+eslint pass
- 2026-03-13: Code review complete — 6 issues fixed, 3 LOW follow-ups logged; status → done
