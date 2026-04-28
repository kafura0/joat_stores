// storefront/lib/tenant.ts — tenant resolution and branding fetch.
// TenantThemeProvider calls getStoreBranding() at layout render time (SSR).
// The Host header sent to the API lets TenantMiddleware resolve the store.

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost/api/v1";

export interface StoreBranding {
  store_name: string;
  slug: string;
  tenant_type: string;
  primary_color: string;
  secondary_color: string;
  font_family: string;
  logo_url: string | null;
  currency: string;
  timezone: string;
}

/**
 * Fetch store branding from the public /api/v1/store/branding/ endpoint.
 * Called server-side in TenantThemeProvider; result is cached for 5 minutes.
 * Returns null if the store is not found or the request fails.
 */
export async function getStoreBranding(
  hostname: string
): Promise<StoreBranding | null> {
  try {
    const res = await fetch(`${API_URL}/store/branding/`, {
      headers: { Host: hostname },
      next: { revalidate: 300 },
    });
    if (!res.ok) return null;
    const json = await res.json();
    return (json.data ?? json) as StoreBranding;
  } catch {
    return null;
  }
}

/**
 * Extracts the store slug from a hostname.
 * Used as a lightweight fallback when the branding API is unavailable.
 */
export function getTenantSlug(hostname: string): string {
  return hostname.split(".")[0] ?? "default";
}
