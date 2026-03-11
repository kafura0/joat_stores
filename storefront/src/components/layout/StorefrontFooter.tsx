/**
 * StorefrontFooter — persistent store footer.
 *
 * Server Component.
 * "Powered by joat stores" slot is always visible at this stage.
 * Plan-gating (hide for higher-tier plans) is implemented in Epic 9.
 *
 * Implementation: Story 1.7
 */

import type { BrandingData } from "@/types/branding";

interface StorefrontFooterProps {
  branding: BrandingData;
}

export default function StorefrontFooter({ branding }: StorefrontFooterProps) {
  return (
    <footer className="mt-auto border-t border-gray-100 bg-white py-6">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center justify-between gap-3 sm:flex-row">
          {/* Store name */}
          <p
            className="text-sm font-medium"
            style={{ color: "var(--color-primary)" }}
          >
            © {new Date().getFullYear()} {branding.store_name}
          </p>

          {/* "Powered by joat stores" — plan-gated in Epic 9 */}
          <p className="text-xs text-gray-400">
            Powered by{" "}
            <span style={{ color: "var(--color-secondary)" }}>
              joat stores
            </span>
          </p>
        </div>
      </div>
    </footer>
  );
}
