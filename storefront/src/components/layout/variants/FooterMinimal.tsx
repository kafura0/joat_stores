import type { BrandingData } from "@/types/branding";

interface Props { branding: BrandingData }

export default function FooterMinimal({ branding }: Props) {
  return (
    <footer
      className="mt-auto py-4 text-center text-xs"
      style={{ color: "var(--color-text-secondary)" }}
    >
      <p>&copy; {new Date().getFullYear()} {branding.store_name}</p>
    </footer>
  );
}
