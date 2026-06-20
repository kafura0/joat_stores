// types/index.ts
// Shared TypeScript type definitions.
// RULE: All types live here — never define types inline in component files.
// RULE: Interfaces prefixed I (IProduct, IOrder); plain types PascalCase (OrderStatus).

// Placeholder — types added as domain stories are implemented.

export type TenantType = "retail" | "restaurant" | "bar" | "contracting";

export type OrderStatus =
  | "pending"
  | "confirmed"
  | "fulfilled"
  | "completed"
  | "cancelled";

export interface IApiResponse<T> {
  data: T;
}

export interface IApiListResponse<T> {
  data: T[];
  meta: {
    count: number;
    next: string | null;
    previous: string | null;
  };
}

export interface IApiError {
  field: string | null;
  message: string;
  code: string;
}

export interface IApiErrorResponse {
  errors: IApiError[];
}

// ---------------------------------------------------------------------------
// Menu (Story 3.2)
// ---------------------------------------------------------------------------

export interface IModifier {
  id: string;
  name: string;
  price_addition: string;
  is_available: boolean;
}

export interface IModifierGroup {
  id: string;
  name: string;
  min_selections: number;
  max_selections: number;
  is_required: boolean;
  modifiers: IModifier[];
}

export interface IMenuItem {
  id: string;
  name: string;
  description: string;
  price: string;
  contains_allergens: boolean;
  allergen_description: string;
  modifier_groups: IModifierGroup[];
}

export interface IMenuSection {
  id: string;
  name: string;
  description: string;
  items: IMenuItem[];
}
