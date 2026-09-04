/**
 * Cart state management — Zustand store.
 * Persists to localStorage across page reloads.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface CartItem {
  variant_id: string;
  product_id: string;
  name: string;
  price: number;
  quantity: number;
  image_url?: string;
}

interface CartStore {
  items: CartItem[];
  coupon_code: string;
  coupon_discount: number;
  isOpen: boolean;

  addItem: (item: Omit<CartItem, "quantity">, quantity?: number) => void;
  removeItem: (variant_id: string) => void;
  updateQuantity: (variant_id: string, quantity: number) => void;
  clearCart: () => void;
  setOpen: (open: boolean) => void;
  setCoupon: (code: string, discount: number) => void;
  clearCoupon: () => void;

  getSubtotal: () => number;
  getTotal: () => number;
  getItemCount: () => number;
}

export const useCartStore = create<CartStore>()(
  persist(
    (set, get) => ({
      items: [],
      coupon_code: "",
      coupon_discount: 0,
      isOpen: false,

      addItem: (item, quantity = 1) => {
        set((state) => {
          const existing = state.items.find(
            (i) => i.variant_id === item.variant_id
          );
          if (existing) {
            return {
              items: state.items.map((i) =>
                i.variant_id === item.variant_id
                  ? { ...i, quantity: i.quantity + quantity }
                  : i
              ),
            };
          }
          return { items: [...state.items, { ...item, quantity }] };
        });
      },

      removeItem: (variant_id) => {
        set((state) => ({
          items: state.items.filter((i) => i.variant_id !== variant_id),
        }));
      },

      updateQuantity: (variant_id, quantity) => {
        if (quantity <= 0) {
          get().removeItem(variant_id);
          return;
        }
        set((state) => ({
          items: state.items.map((i) =>
            i.variant_id === variant_id ? { ...i, quantity } : i
          ),
        }));
      },

      clearCart: () => set({ items: [], coupon_code: "", coupon_discount: 0 }),

      setOpen: (open) => set({ isOpen: open }),

      setCoupon: (code, discount) => set({ coupon_code: code, coupon_discount: discount }),

      clearCoupon: () => set({ coupon_code: "", coupon_discount: 0 }),

      getSubtotal: () => {
        return get().items.reduce(
          (sum, item) => sum + item.price * item.quantity,
          0
        );
      },

      getTotal: () => {
        const subtotal = get().getSubtotal();
        const discount = get().coupon_discount;
        return Math.max(0, subtotal - discount);
      },

      getItemCount: () => {
        return get().items.reduce((sum, item) => sum + item.quantity, 0);
      },
    }),
    {
      name: "joat-cart",
      partialize: (state) => ({
        items: state.items,
        coupon_code: state.coupon_code,
        coupon_discount: state.coupon_discount,
      }),
    }
  )
);
