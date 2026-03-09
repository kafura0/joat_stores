// storefront/src/components/layout/TenantThemeProvider.tsx
// Server Component (no 'use client' — reads hostname server-side)

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
