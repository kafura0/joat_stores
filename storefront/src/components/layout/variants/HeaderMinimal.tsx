import Link from "next/link";
import type { BrandingData } from "@/types/branding";

interface Props { branding: BrandingData }

export default function HeaderMinimal({ branding }: Props) {
  return (
    <header className="w-full" style={{ backgroundColor: "var(--header-bg)" }}>
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center gap-2" aria-label="Home">
          <span className="text-lg font-bold tracking-tight" style={{ color: "var(--header-text)" }}>
            {branding.store_name}
          </span>
        </Link>

        <Link
          href="/cart"
          aria-label="View cart"
          className="rounded-md p-2 transition-colors hover:opacity-80"
          style={{ color: "var(--header-text)" }}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24"
            fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"
            strokeLinejoin="round" aria-hidden="true"
          >
            <circle cx="9" cy="21" r="1" /><circle cx="20" cy="21" r="1" />
            <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6" />
          </svg>
        </Link>
      </div>
    </header>
  );
}
