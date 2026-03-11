/**
 * Admin middleware — auth route guard.
 *
 * Uses a non-sensitive `auth_session` presence cookie (set by lib/auth.ts on
 * login, cleared on logout) to redirect unauthenticated users to /login.
 *
 * IMPORTANT: This is a UX guard, not a security boundary.
 * Security is enforced by the backend API (Bearer token validation).
 * The httpOnly refresh_token cookie has path=/api/v1/auth/ so it is not
 * accessible here; auth_session is a client-set indicator only.
 *
 * Role-based routing (platform_admin → /platform/, etc.) is handled
 * client-side in app/(admin)/layout.tsx after token hydration.
 *
 * Implementation: Story 1.8
 */

import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const SESSION_COOKIE = "auth_session";

export function middleware(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;
  const hasSession = request.cookies.has(SESSION_COOKIE);

  // Already on /login — let through regardless
  if (pathname.startsWith("/login")) {
    return NextResponse.next();
  }

  // No session → redirect to /login
  if (!hasSession) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = "/login";
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths EXCEPT:
     * - _next/static (static files)
     * - _next/image (image optimisation)
     * - favicon.ico
     * - login page (handled above but kept explicit)
     */
    "/((?!_next/static|_next/image|favicon.ico).*)",
  ],
};
