import Link from "next/link";
import type { BrandingData } from "@/types/branding";

interface Props { branding: BrandingData }

export default function HeaderSplit({ branding }: Props) {
  return (
    <header
      className="w-full border-b"
      style={{
        backgroundColor: "var(--header-bg)",
        borderColor: "var(--color-secondary)",
      }}
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center gap-3" aria-label="Home">
          {branding.logo_url ? (
            <img
              src={branding.logo_url}
              alt={`${branding.store_name} logo`}
              width={40}
              height={40}
              className="h-10 w-10 rounded object-contain"
            />
          ) : (
            <span
              className="flex h-10 w-10 items-center justify-center rounded text-lg font-bold"
              style={{ backgroundColor: "var(--color-primary)", color: "var(--header-text)" }}
              aria-hidden="true"
            >
              {branding.store_name.charAt(0).toUpperCase()}
            </span>
          )}
          <span className="text-lg font-semibold" style={{ color: "var(--header-text)" }}>
            {branding.store_name}
          </span>
        </Link>

        <nav className="hidden items-center gap-6 md:flex">
          {["Menu", "About", "Contact"].map((item) => (
            <Link
              key={item}
              href={`/${item.toLowerCase()}`}
              className="text-sm font-medium transition-opacity hover:opacity-80"
              style={{ color: "var(--header-text)" }}
            >
              {item}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
