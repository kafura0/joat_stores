"use client";

import { useState } from "react";
import { Search, ShoppingCart } from "lucide-react";
import { useProducts } from "@/hooks/useProducts";
import { useCartStore } from "@/stores/cartStore";
import { ProductCard } from "@/components/pos/ProductCard";
import { CartItemRow } from "@/components/pos/CartItem";
import { PaymentModal } from "@/components/pos/PaymentModal";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { formatCurrency } from "@/lib/utils";
import { useUIStore } from "@/stores/uiStore";

export default function POSPage() {
  const [search, setSearch] = useState("");
  const [showPayment, setShowPayment] = useState(false);
  const { items, subtotal, tax, total, itemCount, clearCart } = useCartStore();
  const addItem = useCartStore((s) => s.addItem);
  const addToast = useUIStore((s) => s.addToast);

  const { data: products } = useProducts({
    search: search || undefined,
  });

  const handleAddToCart = (
    variantId: number,
    name: string,
    price: string,
    image?: string
  ) => {
    addItem({
      variant_id: variantId,
      product_name: name,
      variant_name: name,
      price,
    });
  };

  return (
    <div className="flex h-screen flex-col bg-[var(--md-surface)] text-[var(--md-on-surface)]">
      {/* Glass header */}
      <header className="flex items-center justify-between border-b border-[var(--md-outline-variant)] bg-[var(--glass-bg)] px-6 py-3 backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-bold bg-gradient-to-r from-[var(--md-primary)] to-[var(--md-tertiary)] bg-clip-text text-transparent">
            JOAT STORES POS
          </h1>
          <span className="rounded-full bg-[var(--md-primary-container)] px-3 py-0.5 text-xs font-medium text-[var(--md-on-primary-container)]">
            Register #01
          </span>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-[var(--md-on-surface-variant)]">
            <ShoppingCart size={20} />
            <span className="rounded-full bg-[var(--md-tertiary)] px-2 py-0.5 text-xs font-bold text-white">
              {itemCount()}
            </span>
          </div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Products Panel — 65% */}
        <div className="flex flex-1 flex-col overflow-hidden border-r border-[var(--md-outline-variant)]">
          {/* Search — glass header */}
          <div className="border-b border-[var(--md-outline-variant)] bg-[var(--glass-bg)] p-4 backdrop-blur-md">
            <div className="relative">
              <Search
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--md-on-surface-variant)]"
              />
              <Input
                placeholder="Search products, barcode or SKU..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9 bg-[var(--md-surface-container)] border-[var(--md-outline-variant)] text-[var(--md-on-surface)] placeholder:text-[var(--md-on-surface-variant)]"
              />
            </div>
          </div>

          {/* Product Grid — glass panel */}
          <div className="flex-1 overflow-y-auto p-4">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
              {products?.data.map((product) => {
                const variant = product.variants?.[0];
                if (!variant) return null;
                return (
                  <ProductCard
                    key={product.id}
                    name={product.name}
                    price={variant.price}
                    image={product.images?.[0]?.image}
                    onAdd={() =>
                      handleAddToCart(
                        variant.id,
                        product.name,
                        variant.price,
                        product.images?.[0]?.image
                      )
                    }
                  />
                );
              })}
            </div>
          </div>
        </div>

        {/* Cart Panel — 35% — glassmorphism */}
        <div className="flex w-[35%] min-w-[320px] flex-col border-l border-[var(--md-outline-variant)] bg-[var(--glass-bg)] backdrop-blur-md">
          <div className="border-b border-[var(--md-outline-variant)] px-4 py-3">
            <h2 className="font-semibold text-[var(--md-on-surface)]">
              Current Order ({itemCount()} items)
            </h2>
          </div>

          {/* Cart Items */}
          <div className="flex-1 overflow-y-auto px-4">
            {items.length === 0 ? (
              <div className="flex h-full items-center justify-center text-sm text-[var(--md-on-surface-variant)]">
                Cart is empty
              </div>
            ) : (
              items.map((item) => (
                <CartItemRow key={item.variant_id} item={item} />
              ))
            )}
          </div>

          {/* Cart Summary — dashed border like template */}
          <div className="border-t border-[var(--md-outline-variant)] p-4">
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-[var(--md-on-surface-variant)]">Subtotal</span>
                <span className="text-[var(--md-on-surface)]">{formatCurrency(subtotal())}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--md-on-surface-variant)]">Tax (16%)</span>
                <span className="text-[var(--md-on-surface)]">{formatCurrency(tax())}</span>
              </div>
              <div className="flex justify-between border-t border-dashed border-[var(--md-outline)] pt-2 text-lg font-bold">
                <span className="text-[var(--md-on-surface)]">Total</span>
                <span className="text-[var(--md-primary)]">{formatCurrency(total())}</span>
              </div>
            </div>

            <div className="mt-4 space-y-2">
              <Button
                onClick={() => setShowPayment(true)}
                disabled={items.length === 0}
                className="w-full bg-gradient-to-r from-[var(--md-success)] to-emerald-600 text-white hover:opacity-90"
              >
                Pay {formatCurrency(total())}
              </Button>
              <Button
                variant="secondary"
                onClick={() => {
                  clearCart();
                  addToast({ type: "info", message: "Cart cleared" });
                }}
                disabled={items.length === 0}
                className="w-full border-[var(--md-outline)] text-[var(--md-on-surface)] hover:bg-[var(--md-surface-variant)]"
              >
                Clear Cart
              </Button>
            </div>
          </div>
        </div>
      </div>

      <PaymentModal open={showPayment} onClose={() => setShowPayment(false)} />
    </div>
  );
}
