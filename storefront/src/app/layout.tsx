/**
 * Root layout — wraps all storefront pages with TenantThemeProvider.
 *
 * TenantThemeProvider (Server Component) handles:
 *   - Branding API fetch (GET /api/v1/store/branding/)
 *   - CSS variable injection (--color-primary, --color-secondary, --font-family)
 *   - StorefrontHeader + StorefrontFooter (persistent layout)
 *   - Suspended store branded 503 page
 *
 * Metadata is tenant-aware via generateMetadata, pulling store_name from
 * the branding API so each store gets <title>{Store Name}</title>.
 *
 * Implementation: Story 1.7
 */

import type { Metadata } from "next";
import { headers } from "next/headers";
import React from "react";

import TenantThemeProvider from "@/components/layout/TenantThemeProvider";
import { fetchTenantBranding } from "@/lib/branding";
import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const headersList = await headers();
  const hostname = headersList.get("host") ?? "localhost";
  const branding = await fetchTenantBranding(hostname);

  return {
    title: branding.store_name,
    description: branding.tagline || `${branding.store_name} — powered by joat stores`,
  };
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        <TenantThemeProvider>{children}</TenantThemeProvider>
      </body>
    </html>
  );
}
