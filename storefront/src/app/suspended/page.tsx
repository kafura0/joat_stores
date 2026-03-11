/**
 * SuspendedPage — branded 503 page for suspended stores.
 *
 * Server Component. Rendered inline by TenantThemeProvider when
 * branding.status === "suspended". The store name and brand colours are
 * already injected via CSS variables by TenantThemeProvider.
 *
 * HTTP 503 status is set on the response by the Django backend for the
 * initial branding fetch. The Next.js page itself does not set the status
 * code (Next.js SSR does not support per-page status codes in App Router
 * without a custom error page — the branded UX is the primary requirement).
 *
 * Implementation: Story 1.7
 */

export default function SuspendedPage() {
  return (
    <div className="flex flex-col items-center justify-center gap-6 py-24 text-center">
      {/* Store initial shown because logo_url may be empty on suspended stores */}
      <div
        className="flex h-20 w-20 items-center justify-center rounded-full text-3xl font-bold text-white"
        style={{ backgroundColor: "var(--color-primary)" }}
        aria-hidden="true"
      >
        ✕
      </div>

      <div className="max-w-sm space-y-2">
        <h1
          className="text-2xl font-semibold"
          style={{ color: "var(--color-primary)" }}
        >
          This store is currently unavailable.
        </h1>
        <p className="text-sm text-gray-500">
          We&apos;re sorry for the inconvenience. Please check back later or
          contact the store directly for assistance.
        </p>
      </div>
    </div>
  );
}
