import type { BrandingData } from "@/types/branding";

interface Props { branding: BrandingData }

export default function FooterSimple({ branding }: Props) {
  return (
    <footer
      className="mt-auto border-t py-6"
      style={{
        backgroundColor: "var(--footer-bg)",
        borderColor: "var(--color-secondary)",
      }}
    >
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-2 px-4 sm:flex-row sm:px-6 lg:px-8">
        <p className="text-sm font-medium" style={{ color: "var(--footer-text)" }}>
          &copy; {new Date().getFullYear()} {branding.store_name}
        </p>
        <p className="text-xs opacity-50" style={{ color: "var(--footer-text)" }}>
          Powered by joat stores
        </p>
      </div>
    </footer>
  );
}
