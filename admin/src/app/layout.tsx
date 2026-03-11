/**
 * Root layout for the admin app.
 *
 * Minimal — auth guard is in middleware.ts and (admin)/layout.tsx.
 * No provider wrapping needed at root: Zustand store is module-level.
 *
 * Implementation: Story 1.8
 */

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "joat stores — Admin",
  description: "Store management portal for joat stores merchants",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
