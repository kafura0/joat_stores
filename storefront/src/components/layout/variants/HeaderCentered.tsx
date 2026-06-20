import Link from "next/link";
import type { BrandingData } from "@/types/branding";

interface Props { branding: BrandingData }

export default function HeaderCentered({ branding }: Props) {
  return (
    <header
      className="w-full border-b"
      style={{
        backgroundColor: "var(--header-bg)",
        borderColor: "var(--color-secondary)",
      }}
    >
      <div className="mx-auto flex max-w-7xl flex-col items-center px-4 py-4 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center gap-3" aria-label="Home">
          {branding.logo_url ? (
            <img
              src={branding.logo_url}
              alt={`${branding.store_name} logo`}
              width={48}
              height={48}
              className="h-12 w-12 rounded object-contain"
            />
          ) : (
            <span
              className="flex h-12 w-12 items-center justify-center rounded text-xl font-bold"
              style={{ backgroundColor: "var(--color-primary)", color: "var(--header-text)" }}
              aria-hidden="true"
            >
              {branding.store_name.charAt(0).toUpperCase()}
            </span>
          )}
          <span className="text-xl font-semibold" style={{ color: "var(--header-text)" }}>
            {branding.store_name}
          </span>
        </Link>
      </div>
    </header>
  );
}
