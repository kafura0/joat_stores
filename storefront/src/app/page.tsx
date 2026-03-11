/**
 * Product listing page shell.
 *
 * Server Component. Renders empty state with product grid structure so
 * Story 4.1 product cards slot in without layout shift.
 *
 * Empty state: "Products coming soon — check back shortly."
 * Grid: 1 col @ 320px, 2 @ 640px, 3 @ 1024px, 4 @ 1280px
 *
 * Implementation: Story 1.7 (shell + empty state)
 * Products populated: Story 4.1
 */

export default function ProductListingPage() {
  // Story 4.1 replaces this with real products from the API.
  const products: unknown[] = [];

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Product grid — responsive, no layout shift when Story 4.1 fills it */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {products.length === 0 ? (
          /* Empty state — AC5 */
          <div className="col-span-full flex flex-col items-center justify-center py-24 text-center">
            <div
              className="mb-6 flex h-16 w-16 items-center justify-center rounded-full"
              style={{ backgroundColor: "var(--color-primary)", opacity: 0.1 }}
              aria-hidden="true"
            />
            <div
              className="mb-4 h-16 w-16 -mt-20 flex items-center justify-center rounded-full text-2xl"
              style={{ color: "var(--color-primary)" }}
              aria-hidden="true"
            >
              🛍️
            </div>
            <h2
              className="text-xl font-semibold"
              style={{ color: "var(--color-primary)" }}
            >
              Products coming soon
            </h2>
            <p className="mt-2 text-sm text-gray-500">
              Check back shortly — we&apos;re stocking up.
            </p>
          </div>
        ) : (
          /* Product card slots — Story 4.1 replaces with real ProductCard components */
          products.map((_, idx) => (
            <div
              key={idx}
              className="product-card-slot h-64 rounded-lg bg-gray-100"
              aria-hidden="true"
            />
          ))
        )}
      </div>
    </div>
  );
}
