import { create } from "zustand";
import type { ICartItem } from "@/types";

interface CartState {
  items: ICartItem[];
  customer_id: number | null;
  payment_method: "cash" | "mpesa" | "card";
  discount: string;
  notes: string;

  addItem: (item: Omit<ICartItem, "quantity" | "id">) => void;
  removeItem: (variant_id: number) => void;
  updateQuantity: (variant_id: number, quantity: number) => void;
  clearCart: () => void;
  setCustomer: (id: number | null) => void;
  setPaymentMethod: (method: "cash" | "mpesa" | "card") => void;
  setDiscount: (discount: string) => void;
  setNotes: (notes: string) => void;

  subtotal: () => string;
  tax: () => string;
  total: () => string;
  itemCount: () => number;
}

export const useCartStore = create<CartState>((set, get) => ({
  items: [],
  customer_id: null,
  payment_method: "cash",
  discount: "0.00",
  notes: "",

  addItem: (item) =>
    set((state) => {
      const existing = state.items.find(
        (i) => i.variant_id === item.variant_id
      );
      if (existing) {
        return {
          items: state.items.map((i) =>
            i.variant_id === item.variant_id
              ? { ...i, quantity: i.quantity + 1 }
              : i
          ),
        };
      }
      return {
        items: [...state.items, { ...item, quantity: 1, id: Date.now() }],
      };
    }),

  removeItem: (variant_id) =>
    set((state) => ({
      items: state.items.filter((i) => i.variant_id !== variant_id),
    })),

  updateQuantity: (variant_id, quantity) =>
    set((state) => ({
      items:
        quantity <= 0
          ? state.items.filter((i) => i.variant_id !== variant_id)
          : state.items.map((i) =>
              i.variant_id === variant_id ? { ...i, quantity } : i
            ),
    })),

  clearCart: () =>
    set({ items: [], customer_id: null, notes: "", discount: "0.00" }),
  setCustomer: (id) => set({ customer_id: id }),
  setPaymentMethod: (method) => set({ payment_method: method }),
  setDiscount: (discount) => set({ discount }),
  setNotes: (notes) => set({ notes }),

  subtotal: () => {
    const { items } = get();
    return items
      .reduce((sum, item) => sum + parseFloat(item.price) * item.quantity, 0)
      .toFixed(2);
  },

  tax: () => {
    const sub = parseFloat(get().subtotal());
    return (sub * 0.16).toFixed(2);
  },

  total: () => {
    const sub = parseFloat(get().subtotal());
    const tax = parseFloat(get().tax());
    const discount = parseFloat(get().discount);
    return (sub + tax - discount).toFixed(2);
  },

  itemCount: () =>
    get().items.reduce((sum, item) => sum + item.quantity, 0),
}));
