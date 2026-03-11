/**
 * Root layout — wraps all storefront pages with TenantThemeProvider.
 *
 * TenantThemeProvider (Server Component) handles:
 *   - Branding API fetch (GET /api/v1/store/branding/)
 *   - CSS variable injection (--color-primary, --color-secondary, --font-family)
 *   - StorefrontHeader + StorefrontFooter (persistent layout)
 *   - Suspended store branded 503 page
 *
 * Implementation: Story 1.7
 */

import type { Metadata } from "next";
import React from "react";

import TenantThemeProvider from "@/components/layout/TenantThemeProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: "joat stores",
  description: "Your store, powered by joat stores",
};

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
