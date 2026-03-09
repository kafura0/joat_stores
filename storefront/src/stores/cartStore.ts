// storefront/stores/cartStore.ts
// Cart state management.
// Full implementation in Story 4.1 (Retail Cart).

import { create } from "zustand";

interface CartStore {
  // TODO: Story 4.1 — add cart items, totals, open/close state
  isOpen: boolean;
  setOpen: (open: boolean) => void;
}

export const useCartStore = create<CartStore>((set) => ({
  isOpen: false,
  setOpen: (open) => set({ isOpen: open }),
}));
