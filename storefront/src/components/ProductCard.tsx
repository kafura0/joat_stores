"use client";

import { useState } from "react";
import { Plus, Minus, ShoppingCart } from "lucide-react";
import { useCartStore } from "@/stores/cartStore";
import type { IProduct } from "@/types/product";

interface ProductCardProps {
  product: IProduct;
}

export default function ProductCard({ product }: ProductCardProps) {
  const addItem = useCartStore((s) => s.addItem);
  const [quantity, setQuantity] = useState(1);

  const defaultVariant = product.variants?.[0];
  const price = defaultVariant ? parseFloat(defaultVariant.price) : 0;
  const inStock = defaultVariant
    ? defaultVariant.is_available && defaultVariant.inventory_count > 0
    : false;
  const imageUrl = product.images?.[0]?.image;

  const handleAdd = () => {
    if (!defaultVariant) return;
    addItem(
      {
        variant_id: defaultVariant.id,
        product_id: product.id,
        name: product.name,
        price,
        image_url: imageUrl,
      },
      quantity
    );
    setQuantity(1);
  };

  return (
    <div className="group relative overflow-hidden rounded-2xl border border-[var(--md-outline-variant)] bg-[var(--md-surface)] shadow-sm transition-all hover:shadow-md">
      {/* Image */}
      <div className="relative aspect-square overflow-hidden bg-[var(--md-surface-container)]">
        {imageUrl ? (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={imageUrl}
            alt={product.name}
            className="h-full w-full object-cover transition-transform group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-4xl text-[var(--md-on-surface-variant)] opacity-30">
            📦
          </div>
        )}
        {!inStock && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/40">
            <span className="rounded-full bg-white/90 px-3 py-1 text-sm font-medium text-gray-800">
              Out of Stock
            </span>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        {product.category && (
          <p className="mb-1 text-xs font-medium uppercase tracking-wider text-[var(--md-primary)]">
            {product.category.name}
          </p>
        )}
        <h3 className="text-base font-semibold text-[var(--md-on-surface)] line-clamp-2">
          {product.name}
        </h3>
        {product.description && (
          <p className="mt-1 text-sm text-[var(--md-on-surface-variant)] line-clamp-2">
            {product.description}
          </p>
        )}

        <div className="mt-3 flex items-end justify-between">
          <p className="text-lg font-bold text-[var(--md-on-surface)]">
            KES {price.toLocaleString()}
          </p>

          {inStock && (
            <div className="flex items-center gap-2">
              {/* Quantity controls */}
              <div className="flex items-center overflow-hidden rounded-lg border border-[var(--md-outline)]">
                <button
                  onClick={() => setQuantity(Math.max(1, quantity - 1))}
                  className="px-2 py-1 text-[var(--md-on-surface-variant)] hover:bg-[var(--md-surface-container)]"
                  aria-label="Decrease quantity"
                >
                  <Minus className="h-3 w-3" />
                </button>
                <span className="min-w-[2rem] text-center text-sm font-medium">
                  {quantity}
                </span>
                <button
                  onClick={() => setQuantity(quantity + 1)}
                  className="px-2 py-1 text-[var(--md-on-surface-variant)] hover:bg-[var(--md-surface-container)]"
                  aria-label="Increase quantity"
                >
                  <Plus className="h-3 w-3" />
                </button>
              </div>

              {/* Add to cart */}
              <button
                onClick={handleAdd}
                className="flex items-center gap-1 rounded-lg px-3 py-2 text-sm font-medium text-white transition-colors"
                style={{ backgroundColor: "var(--color-primary)" }}
              >
                <ShoppingCart className="h-4 w-4" />
                Add
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
