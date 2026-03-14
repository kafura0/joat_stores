/**
 * Story 3.2 — Public Menu Page
 *
 * Server Component (SSR). Fetches the public menu from the backend and renders
 * sections + items for the current service window. No authentication required.
 *
 * URL: /menu/ (tenant resolved from domain by middleware.ts)
 */

import type { Metadata } from "next";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface IModifier {
  id: string;
  name: string;
  price_addition: string;
  is_available: boolean;
}

interface IModifierGroup {
  id: string;
  name: string;
  min_selections: number;
  max_selections: number;
  is_required: boolean;
  modifiers: IModifier[];
}

interface IMenuItem {
  id: string;
  name: string;
  description: string;
  price: string;
  contains_allergens: boolean;
  allergen_description: string;
  modifier_groups: IModifierGroup[];
}

interface IMenuSection {
  id: string;
  name: string;
  description: string;
  items: IMenuItem[];
}

// ---------------------------------------------------------------------------
// Data fetching
// ---------------------------------------------------------------------------

async function fetchPublicMenu(storeId: string): Promise<IMenuSection[]> {
  const apiUrl = process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL;
  const res = await fetch(`${apiUrl}/api/v1/restaurant/public-menu/`, {
    headers: {
      "X-Store-ID": storeId,
      "Content-Type": "application/json",
    },
    // No-store: always fresh (SSR — each request fetches live data)
    cache: "no-store",
  });

  if (!res.ok) return [];
  const json = await res.json();
  return (json.data as IMenuSection[]) ?? [];
}

// ---------------------------------------------------------------------------
// Metadata
// ---------------------------------------------------------------------------

export const metadata: Metadata = {
  title: "Menu",
  description: "Browse our full menu",
};

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function PublicMenuPage() {
  // Store ID injected by middleware.ts into request headers / cookies
  // For SSR, we read from the NEXT_PUBLIC_STORE_ID env or a cookie set by middleware
  const storeId = process.env.NEXT_PUBLIC_STORE_ID ?? "";
  const sections = await fetchPublicMenu(storeId);

  if (sections.length === 0) {
    return (
      <main className="min-h-screen p-4">
        <p className="text-center text-gray-500 mt-16">
          Menu is not available at this time. Please check back later.
        </p>
      </main>
    );
  }

  return (
    <main className="min-h-screen max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Our Menu</h1>

      {sections.map((section) => (
        <section key={section.id} className="mb-8">
          <h2 className="text-xl font-semibold border-b border-gray-200 pb-2 mb-4">
            {section.name}
          </h2>
          {section.description && (
            <p className="text-sm text-gray-500 mb-3">{section.description}</p>
          )}

          <ul className="space-y-4">
            {section.items.map((item) => (
              <li key={item.id} className="flex justify-between items-start gap-4">
                <div className="flex-1">
                  <p className="font-medium text-base">{item.name}</p>
                  {item.description && (
                    <p className="text-sm text-gray-600 mt-0.5">{item.description}</p>
                  )}
                  {item.contains_allergens && (
                    <p className="text-xs text-amber-600 mt-1">
                      ⚠ Contains allergens
                      {item.allergen_description
                        ? `: ${item.allergen_description}`
                        : ""}
                    </p>
                  )}
                  {item.modifier_groups.length > 0 && (
                    <div className="mt-2 space-y-1">
                      {item.modifier_groups.map((group) => (
                        <div key={group.id} className="text-xs text-gray-500">
                          <span className="font-medium">{group.name}:</span>{" "}
                          {group.modifiers
                            .filter((m) => m.is_available)
                            .map((m) =>
                              parseFloat(m.price_addition) > 0
                                ? `${m.name} (+KES ${m.price_addition})`
                                : m.name
                            )
                            .join(", ")}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <p className="text-base font-semibold whitespace-nowrap">
                  KES {item.price}
                </p>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </main>
  );
}
