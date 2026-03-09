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
