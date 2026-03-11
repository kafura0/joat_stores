/**
 * TenantThemeProvider — Server Component.
 *
 * Fetches live branding from GET /api/v1/store/branding/ on every SSR request
 * and injects CSS variables into the page root so all components can use:
 *   var(--color-primary), var(--color-secondary), var(--font-family)
 *
 * Suspended stores: renders branded SuspendedPage inline.
 * Errors: falls back to DEFAULT_BRANDING — never crashes SSR.
 *
 * RULE: Brand colours must NEVER be hardcoded in component files.
 * Always use var(--color-primary) in Tailwind or inline styles.
 *
 * Implementation: Story 1.7
 */

import { headers } from "next/headers";
import React from "react";

import StorefrontFooter from "@/components/layout/StorefrontFooter";
import StorefrontHeader from "@/components/layout/StorefrontHeader";
import { fetchTenantBranding } from "@/lib/branding";
import { DEFAULT_BRANDING } from "@/types/branding";
import SuspendedPage from "@/app/suspended/page";

export default async function TenantThemeProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const headersList = await headers();
  const hostname = headersList.get("host") ?? "localhost";

  const branding = await fetchTenantBranding(hostname);

  const cssVariables = {
    "--color-primary": branding.primary_color ?? DEFAULT_BRANDING.primary_color,
    "--color-secondary":
      branding.secondary_color ?? DEFAULT_BRANDING.secondary_color,
    "--font-family": `${branding.font_family ?? DEFAULT_BRANDING.font_family}, sans-serif`,
  } as React.CSSProperties;

  // Suspended store → render branded 503 page, not children
  if (branding.status === "suspended") {
    return (
      <div style={cssVariables} className="flex min-h-screen flex-col">
        <StorefrontHeader branding={branding} />
        <main className="flex flex-1 items-center justify-center px-4">
          <SuspendedPage />
        </main>
        <StorefrontFooter branding={branding} />
      </div>
    );
  }

  return (
    <div style={cssVariables} className="flex min-h-screen flex-col">
      <StorefrontHeader branding={branding} />
      <main className="flex-1">{children}</main>
      <StorefrontFooter branding={branding} />
    </div>
  );
}
