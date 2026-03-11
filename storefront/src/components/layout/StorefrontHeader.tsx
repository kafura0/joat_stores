/**
 * StorefrontHeader — persistent store header.
 *
 * Server Component — no client JS for above-fold content (AC6: <200KB payload).
 * Cart icon is a placeholder link; full cart functionality added in Story 4.2.
 *
 * Implementation: Story 1.7
 */

import Link from "next/link";

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

        {/* Cart icon — placeholder, wired in Story 4.2 */}
        <Link
          href="/cart"
          aria-label="View cart"
          className="relative rounded-md p-2 transition-colors hover:bg-gray-100"
        >
          {/* Inline SVG — no icon library import (AC6: bundle size) */}
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
            style={{ color: "var(--color-primary)" }}
          >
            <circle cx="9" cy="21" r="1" />
            <circle cx="20" cy="21" r="1" />
            <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6" />
          </svg>
        </Link>
      </div>
    </header>
  );
}
