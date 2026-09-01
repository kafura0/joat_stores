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
    <div className="flex h-screen flex-col">
      {/* Header */}
      <header className="flex items-center justify-between border-b bg-white px-4 py-3">
        <h1 className="text-lg font-bold">JOAT STORES POS</h1>
        <div className="flex items-center gap-2">
          <ShoppingCart size={20} />
          <span className="rounded-full bg-blue-600 px-2 py-0.5 text-xs text-white">
            {itemCount()}
          </span>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Products Panel */}
        <div className="flex flex-1 flex-col overflow-hidden border-r">
          {/* Search */}
          <div className="border-b bg-white p-4">
            <div className="relative">
              <Search
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
              />
              <Input
                placeholder="Search products..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
          </div>

          {/* Product Grid */}
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

        {/* Cart Panel */}
        <div className="flex w-80 flex-col bg-white">
          <div className="border-b px-4 py-3">
            <h2 className="font-semibold">
              Cart ({itemCount()} items)
            </h2>
          </div>

          {/* Cart Items */}
          <div className="flex-1 overflow-y-auto px-4">
            {items.length === 0 ? (
              <div className="flex h-full items-center justify-center text-sm text-gray-400">
                Cart is empty
              </div>
            ) : (
              items.map((item) => (
                <CartItemRow key={item.variant_id} item={item} />
              ))
            )}
          </div>

          {/* Cart Summary */}
          <div className="border-t bg-gray-50 p-4">
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Subtotal</span>
                <span>{formatCurrency(subtotal())}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Tax (16%)</span>
                <span>{formatCurrency(tax())}</span>
              </div>
              <div className="flex justify-between border-t pt-2 text-lg font-bold">
                <span>Total</span>
                <span>{formatCurrency(total())}</span>
              </div>
            </div>

            <div className="mt-4 space-y-2">
              <Button
                onClick={() => setShowPayment(true)}
                disabled={items.length === 0}
                className="w-full"
              >
                Pay Now
              </Button>
              <Button
                variant="secondary"
                onClick={() => {
                  clearCart();
                  addToast({ type: "info", message: "Cart cleared" });
                }}
                disabled={items.length === 0}
                className="w-full"
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
