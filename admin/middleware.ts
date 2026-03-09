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
