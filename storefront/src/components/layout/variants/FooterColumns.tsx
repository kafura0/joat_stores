import type { BrandingData } from "@/types/branding";

interface Props { branding: BrandingData }

export default function FooterColumns({ branding }: Props) {
  return (
    <footer
      className="mt-auto border-t py-8"
      style={{
        backgroundColor: "var(--footer-bg)",
        borderColor: "var(--color-secondary)",
      }}
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid gap-8 sm:grid-cols-3">
          <div>
            <p className="text-sm font-semibold" style={{ color: "var(--footer-text)" }}>
              {branding.store_name}
            </p>
            {branding.tagline && (
              <p className="mt-1 text-xs opacity-70" style={{ color: "var(--footer-text)" }}>
                {branding.tagline}
              </p>
            )}
          </div>
          <div>
            <p className="text-sm font-semibold" style={{ color: "var(--footer-text)" }}>
              Quick Links
            </p>
            <ul className="mt-2 space-y-1 text-xs opacity-70" style={{ color: "var(--footer-text)" }}>
              <li>Menu</li>
              <li>About</li>
              <li>Contact</li>
            </ul>
          </div>
          <div className="text-right text-xs opacity-50" style={{ color: "var(--footer-text)" }}>
            <p>&copy; {new Date().getFullYear()} {branding.store_name}</p>
            <p className="mt-1">Powered by joat stores</p>
          </div>
        </div>
      </div>
    </footer>
  );
}
