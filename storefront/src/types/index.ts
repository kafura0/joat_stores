export * from "@joat/shared/types";

// Storefront-specific menu types (not in shared)
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
