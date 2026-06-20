/**
 * Storefront middleware — tenant resolution from Host header.
 *
 * Extracts the store identifier from the request's Host header and
 * injects it as X-Store-ID into request headers forwarded to the backend.
 * Also exposes it via a `x-store-id` response header for client-side use.
 *
 * In local dev, falls back to NEXT_PUBLIC_STORE_ID env var when no
 * subdomain is present (localhost).
 *
 * Implementation: Story 1.2 (tenant resolution for storefront SSR)
 */

import { NextRequest, NextResponse } from "next/server";

const DEV_STORE_ID = process.env.NEXT_PUBLIC_STORE_ID;

export function middleware(request: NextRequest) {
  const hostname = request.headers.get("host")?.split(":")[0]?.toLowerCase() ?? "";

  // Skip for non-storefront paths
  const { pathname } = request.nextUrl;
  if (
    pathname.startsWith("/_next/") ||
    pathname.startsWith("/api/") ||
    pathname === "/favicon.ico"
  ) {
    return NextResponse.next();
  }

  // Resolve store identifier
  let storeId = "";

  if (hostname === "localhost" || hostname.endsWith(".local")) {
    storeId = DEV_STORE_ID ?? "";
  } else {
    // In production: map hostname to store domain slug.
    // The backend's TenantMiddleware resolves the store from the Host header
    // directly, so no lookup needed here. We just pass the Host through.
    // For SSR pages needing X-Store-ID, derive from subdomain.
    const subdomain = hostname.split(".")[0];
    if (subdomain && subdomain !== "www") {
      storeId = subdomain;
    }
  }

  const requestHeaders = new Headers(request.headers);
  if (storeId) {
    requestHeaders.set("X-Store-ID", storeId);
  }

  const response = NextResponse.next({
    request: { headers: requestHeaders },
  });

  if (storeId) {
    response.headers.set("x-store-id", storeId);
  }

  return response;
}
