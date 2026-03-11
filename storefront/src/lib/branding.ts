/**
 * Server-side branding fetch for TenantThemeProvider.
 *
 * Calls GET /api/v1/store/branding/ with X-Store-ID derived from hostname.
 * Returns DEFAULT_BRANDING on any error — never throws, never crashes SSR.
 *
 * cache: 'no-store' — each SSR request gets fresh branding (store owners
 * can update colours/logo and see changes immediately).
 *
 * Implementation: Story 1.7
 */

import { BrandingData, DEFAULT_BRANDING } from "@/types/branding";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost/api/v1";

/**
 * Extracts the store identifier from a hostname.
 * e.g. "nairobieats.joat.com" → uses as domain lookup via Host header.
 * In dev, falls back to X-Store-ID header if NEXT_PUBLIC_STORE_ID is set.
 */
function getStoreIdHeader(): Record<string, string> {
  const storeId = process.env.NEXT_PUBLIC_STORE_ID;
  if (storeId) {
    return { "X-Store-ID": storeId };
  }
  return {};
}

export async function fetchTenantBranding(
  hostname: string
): Promise<BrandingData> {
  try {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      Host: hostname,
      ...getStoreIdHeader(),
    };

    const res = await fetch(`${API_URL}/store/branding/`, {
      headers,
      cache: "no-store",
    });

    // 503 for suspended stores — still parse the body (it contains store_name)
    if (res.status === 503 || res.ok) {
      const json = (await res.json()) as { data: BrandingData };
      return json.data ?? DEFAULT_BRANDING;
    }

    // 404 or other errors — graceful fallback
    return DEFAULT_BRANDING;
  } catch {
    // Network error, parse error, etc. — never crash SSR
    return DEFAULT_BRANDING;
  }
}
