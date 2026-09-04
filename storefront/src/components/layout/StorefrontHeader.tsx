/**
 * StorefrontHeader — persistent store header.
 *
 * Server Component — no client JS for above-fold content (AC6: <200KB payload).
 * Cart icon is a client component that reads from Zustand cart store.
 *
 * Implementation: Story 1.7
 */

import Link from "next/link";

import CartIcon from "@/components/CartIcon";
import type { BrandingData } from "@/types/branding";

interface StorefrontHeaderProps {
  branding: BrandingData;
}

export default function StorefrontHeader({ branding }: StorefrontHeaderProps) {
  return (
    <header
      className="w-full border-b border-gray-200 bg-white"
      style={{ borderColor: "var(--color-secondary)" }}
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
        {/* Logo + Store name */}
        <Link href="/" className="flex items-center gap-3" aria-label="Home">
          {branding.logo_url ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={branding.logo_url}
              alt={`${branding.store_name} logo`}
              width={40}
              height={40}
              className="h-10 w-10 rounded object-contain"
            />
          ) : (
            /* Fallback: coloured initial block */
            <span
              className="flex h-10 w-10 items-center justify-center rounded text-lg font-bold text-white"
              style={{ backgroundColor: "var(--color-primary)" }}
              aria-hidden="true"
            >
              {branding.store_name.charAt(0).toUpperCase()}
            </span>
          )}
          <span
            className="text-xl font-semibold"
            style={{ color: "var(--color-primary)" }}
          >
            {branding.store_name}
          </span>
        </Link>

        {/* Cart icon with badge */}
        <CartIcon />
      </div>
    </header>
  );
}
