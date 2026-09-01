"use client";

import { Minus, Plus, Trash2 } from "lucide-react";
import { formatCurrency } from "@/lib/utils";
import { useCartStore } from "@/stores/cartStore";
import type { ICartItem } from "@/types";

export function CartItemRow({ item }: { item: ICartItem }) {
  const { updateQuantity, removeItem } = useCartStore();

  return (
    <div className="flex items-center justify-between border-b py-3">
      <div className="min-w-0 flex-1">
        <p className="truncate font-medium">{item.product_name}</p>
        <p className="text-sm text-gray-500">{formatCurrency(item.price)}</p>
      </div>
      <div className="flex items-center gap-1">
        <button
          onClick={() => updateQuantity(item.variant_id, item.quantity - 1)}
          className="rounded p-1 hover:bg-gray-100"
          style={{ minHeight: 48, minWidth: 48 }}
        >
          <Minus size={16} />
        </button>
        <span className="w-8 text-center font-medium">{item.quantity}</span>
        <button
          onClick={() => updateQuantity(item.variant_id, item.quantity + 1)}
          className="rounded p-1 hover:bg-gray-100"
          style={{ minHeight: 48, minWidth: 48 }}
        >
          <Plus size={16} />
        </button>
        <button
          onClick={() => removeItem(item.variant_id)}
          className="rounded p-1 text-red-500 hover:bg-red-50"
          style={{ minHeight: 48, minWidth: 48 }}
        >
          <Trash2 size={16} />
        </button>
      </div>
    </div>
  );
}
