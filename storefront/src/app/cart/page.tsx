"use client";

import { useState } from "react";
import Link from "next/link";
import { Trash2, Plus, Minus, ShoppingBag, ArrowRight } from "lucide-react";
import { useCartStore } from "@/stores/cartStore";
import { api } from "@/lib/api";

export default function CartPage() {
  const {
    items,
    coupon_code,
    coupon_discount,
    removeItem,
    updateQuantity,
    clearCart,
    setCoupon,
    clearCoupon,
    getSubtotal,
    getTotal,
    getItemCount,
  } = useCartStore();

  const [couponInput, setCouponInput] = useState(coupon_code);
  const [couponLoading, setCouponLoading] = useState(false);
  const [couponError, setCouponError] = useState<string | null>(null);

  const subtotal = getSubtotal();
  const total = getTotal();
  const itemCount = getItemCount();

  const handleApplyCoupon = async () => {
    if (!couponInput.trim()) return;
    setCouponLoading(true);
    setCouponError(null);

    try {
      const { data } = await api.post("/coupons/validate/", {
        code: couponInput.trim(),
        subtotal: subtotal.toString(),
      });

      if (data.valid) {
        setCoupon(data.code, parseFloat(data.discount_amount));
      } else {
        setCouponError(data.message || "Invalid coupon");
      }
    } catch (err: any) {
      setCouponError(
        err.response?.data?.message || "Failed to validate coupon"
      );
    } finally {
      setCouponLoading(false);
    }
  };

  const handleRemoveCoupon = () => {
    clearCoupon();
    setCouponInput("");
    setCouponError(null);
  };

  if (items.length === 0) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-24 text-center sm:px-6 lg:px-8">
        <ShoppingBag className="mx-auto mb-6 h-16 w-16 text-[var(--md-on-surface-variant)] opacity-40" />
        <h1 className="text-2xl font-bold text-[var(--md-on-surface)]">
          Your cart is empty
        </h1>
        <p className="mt-2 text-[var(--md-on-surface-variant)]">
          Add some products to get started.
        </p>
        <Link
          href="/"
          className="mt-6 inline-flex items-center gap-2 rounded-xl px-6 py-3 text-sm font-medium text-white"
          style={{ backgroundColor: "var(--color-primary)" }}
        >
          Continue Shopping <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-[var(--md-on-surface)]">
          Cart ({itemCount} {itemCount === 1 ? "item" : "items"})
        </h1>
        <button
          onClick={clearCart}
          className="text-sm text-[var(--md-error)] hover:underline"
        >
          Clear Cart
        </button>
      </div>

      {/* Cart Items */}
      <div className="space-y-4 mb-8">
        {items.map((item) => (
          <div
            key={item.variant_id}
            className="flex items-center gap-4 rounded-xl border border-[var(--md-outline-variant)] bg-[var(--md-surface)] p-4"
          >
            {/* Image */}
            <div className="h-20 w-20 flex-shrink-0 overflow-hidden rounded-lg bg-[var(--md-surface-container)]">
              {item.image_url ? (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img
                  src={item.image_url}
                  alt={item.name}
                  className="h-full w-full object-cover"
                />
              ) : (
                <div className="flex h-full items-center justify-center text-2xl opacity-30">
                  📦
                </div>
              )}
            </div>

            {/* Details */}
            <div className="flex-1 min-w-0">
              <h3 className="font-medium text-[var(--md-on-surface)] truncate">
                {item.name}
              </h3>
              <p className="text-sm text-[var(--md-on-surface-variant)]">
                KES {item.price.toLocaleString()} each
              </p>
            </div>

            {/* Quantity */}
            <div className="flex items-center gap-2">
              <div className="flex items-center overflow-hidden rounded-lg border border-[var(--md-outline)]">
                <button
                  onClick={() =>
                    updateQuantity(item.variant_id, item.quantity - 1)
                  }
                  className="px-2 py-1 text-[var(--md-on-surface-variant)] hover:bg-[var(--md-surface-container)]"
                >
                  <Minus className="h-3 w-3" />
                </button>
                <span className="min-w-[2rem] text-center text-sm font-medium">
                  {item.quantity}
                </span>
                <button
                  onClick={() =>
                    updateQuantity(item.variant_id, item.quantity + 1)
                  }
                  className="px-2 py-1 text-[var(--md-on-surface-variant)] hover:bg-[var(--md-surface-container)]"
                >
                  <Plus className="h-3 w-3" />
                </button>
              </div>
              <p className="w-24 text-right font-semibold text-[var(--md-on-surface)]">
                KES {(item.price * item.quantity).toLocaleString()}
              </p>
              <button
                onClick={() => removeItem(item.variant_id)}
                className="p-1 text-[var(--md-on-surface-variant)] hover:text-[var(--md-error)]"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Coupon */}
      <div className="rounded-xl border border-[var(--md-outline-variant)] bg-[var(--md-surface)] p-4 mb-6">
        <h3 className="mb-3 font-medium text-[var(--md-on-surface)]">
          Coupon Code
        </h3>
        {coupon_code ? (
          <div className="flex items-center justify-between">
            <div>
              <span className="font-mono font-bold text-[var(--md-primary)]">
                {coupon_code}
              </span>
              <span className="ml-2 text-sm text-[var(--md-on-surface-variant)]">
                — KES {coupon_discount.toLocaleString()} discount
              </span>
            </div>
            <button
              onClick={handleRemoveCoupon}
              className="text-sm text-[var(--md-error)] hover:underline"
            >
              Remove
            </button>
          </div>
        ) : (
          <div className="flex gap-2">
            <input
              type="text"
              value={couponInput}
              onChange={(e) => setCouponInput(e.target.value.toUpperCase())}
              placeholder="Enter coupon code"
              className="flex-1 rounded-lg border border-[var(--md-outline)] bg-[var(--md-surface-container)] px-3 py-2 text-sm focus:border-[var(--md-primary)] focus:outline-none"
            />
            <button
              onClick={handleApplyCoupon}
              disabled={couponLoading || !couponInput.trim()}
              className="rounded-lg px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              style={{ backgroundColor: "var(--color-primary)" }}
            >
              {couponLoading ? "Checking..." : "Apply"}
            </button>
          </div>
        )}
        {couponError && (
          <p className="mt-2 text-sm text-[var(--md-error)]">{couponError}</p>
        )}
      </div>

      {/* Summary */}
      <div className="rounded-xl border border-[var(--md-outline-variant)] bg-[var(--md-surface)] p-6">
        <div className="space-y-3">
          <div className="flex justify-between text-sm">
            <span className="text-[var(--md-on-surface-variant)]">Subtotal</span>
            <span className="text-[var(--md-on-surface)]">
              KES {subtotal.toLocaleString()}
            </span>
          </div>
          {coupon_discount > 0 && (
            <div className="flex justify-between text-sm">
              <span className="text-[var(--md-error)]">Discount</span>
              <span className="text-[var(--md-error)]">
                - KES {coupon_discount.toLocaleString()}
              </span>
            </div>
          )}
          <div className="border-t border-[var(--md-outline-variant)] pt-3">
            <div className="flex justify-between">
              <span className="text-lg font-bold text-[var(--md-on-surface)]">
                Total
              </span>
              <span className="text-lg font-bold text-[var(--md-on-surface)]">
                KES {total.toLocaleString()}
              </span>
            </div>
          </div>
        </div>

        <Link
          href="/checkout"
          className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl px-6 py-3 text-sm font-medium text-white transition-opacity hover:opacity-90"
          style={{ backgroundColor: "var(--color-primary)" }}
        >
          Proceed to Checkout <ArrowRight className="h-4 w-4" />
        </Link>

        <Link
          href="/"
          className="mt-3 flex w-full items-center justify-center rounded-xl border border-[var(--md-outline)] px-6 py-3 text-sm font-medium text-[var(--md-on-surface)] hover:bg-[var(--md-surface-container)]"
        >
          Continue Shopping
        </Link>
      </div>
    </div>
  );
}
