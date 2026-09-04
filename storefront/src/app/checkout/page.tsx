"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { useCartStore } from "@/stores/cartStore";
import { api } from "@/lib/api";

type CheckoutStep = "form" | "processing" | "success" | "error";

export default function CheckoutPage() {
  const router = useRouter();
  const {
    items,
    coupon_code,
    coupon_discount,
    getSubtotal,
    getTotal,
    clearCart,
  } = useCartStore();

  const [step, setStep] = useState<CheckoutStep>("form");
  const [phone, setPhone] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [orderId, setOrderId] = useState<string | null>(null);

  const subtotal = getSubtotal();
  const total = getTotal();

  // Redirect if cart is empty
  if (items.length === 0 && step === "form") {
    return (
      <div className="mx-auto max-w-2xl px-4 py-24 text-center sm:px-6 lg:px-8">
        <AlertCircle className="mx-auto mb-6 h-16 w-16 text-[var(--md-on-surface-variant)] opacity-40" />
        <h1 className="text-2xl font-bold text-[var(--md-on-surface)]">
          Nothing to checkout
        </h1>
        <p className="mt-2 text-[var(--md-on-surface-variant)]">
          Add some products to your cart first.
        </p>
        <Link
          href="/"
          className="mt-6 inline-flex items-center gap-2 rounded-xl px-6 py-3 text-sm font-medium text-white"
          style={{ backgroundColor: "var(--color-primary)" }}
        >
          Browse Products
        </Link>
      </div>
    );
  }

  const handleCheckout = async () => {
    if (!phone.trim()) return;

    setStep("processing");
    setErrorMessage("");

    try {
      const payload: Record<string, unknown> = {
        phone: phone.trim(),
        name: name.trim(),
        email: email.trim(),
        cart_ref: "web-" + Date.now(),
        items: items.map((item) => ({
          variant_id: item.variant_id,
          product_id: item.product_id,
          quantity: item.quantity,
        })),
      };

      if (coupon_code) {
        payload.coupon_code = coupon_code;
      }

      const { data } = await api.post("/checkout/", payload);

      if (data.errors) {
        const err = data.errors[0];
        setErrorMessage(err.message || "Checkout failed");
        setStep("error");
        return;
      }

      setOrderId(data.order_id || data.id);
      setStep("success");
      clearCart();
    } catch (err: any) {
      const msg =
        err.response?.data?.errors?.[0]?.message ||
        err.response?.data?.message ||
        "Checkout failed. Please try again.";
      setErrorMessage(msg);
      setStep("error");
    }
  };

  // Success state
  if (step === "success") {
    return (
      <div className="mx-auto max-w-2xl px-4 py-24 text-center sm:px-6 lg:px-8">
        <CheckCircle2 className="mx-auto mb-6 h-16 w-16 text-green-500" />
        <h1 className="text-2xl font-bold text-[var(--md-on-surface)]">
          Order Placed!
        </h1>
        <p className="mt-2 text-[var(--md-on-surface-variant)]">
          Check your phone for the M-Pesa payment prompt.
        </p>
        {orderId && (
          <p className="mt-4 text-sm text-[var(--md-on-surface-variant)]">
            Order ID: <span className="font-mono font-bold">{orderId}</span>
          </p>
        )}
        <Link
          href="/"
          className="mt-8 inline-flex items-center gap-2 rounded-xl px-6 py-3 text-sm font-medium text-white"
          style={{ backgroundColor: "var(--color-primary)" }}
        >
          Back to Shop
        </Link>
      </div>
    );
  }

  // Error state
  if (step === "error") {
    return (
      <div className="mx-auto max-w-2xl px-4 py-24 text-center sm:px-6 lg:px-8">
        <AlertCircle className="mx-auto mb-6 h-16 w-16 text-[var(--md-error)]" />
        <h1 className="text-2xl font-bold text-[var(--md-on-surface)]">
          Checkout Failed
        </h1>
        <p className="mt-2 text-[var(--md-error)]">{errorMessage}</p>
        <div className="mt-8 flex justify-center gap-4">
          <button
            onClick={() => setStep("form")}
            className="rounded-xl px-6 py-3 text-sm font-medium text-white"
            style={{ backgroundColor: "var(--color-primary)" }}
          >
            Try Again
          </button>
          <Link
            href="/cart"
            className="rounded-xl border border-[var(--md-outline)] px-6 py-3 text-sm font-medium text-[var(--md-on-surface)] hover:bg-[var(--md-surface-container)]"
          >
            Back to Cart
          </Link>
        </div>
      </div>
    );
  }

  // Processing state
  if (step === "processing") {
    return (
      <div className="mx-auto max-w-2xl px-4 py-24 text-center sm:px-6 lg:px-8">
        <Loader2 className="mx-auto mb-6 h-16 w-16 animate-spin text-[var(--md-primary)]" />
        <h1 className="text-2xl font-bold text-[var(--md-on-surface)]">
          Processing Your Order...
        </h1>
        <p className="mt-2 text-[var(--md-on-surface-variant)]">
          Please wait while we initiate the M-Pesa payment.
        </p>
      </div>
    );
  }

  // Form state
  return (
    <div className="mx-auto max-w-2xl px-4 py-8 sm:px-6 lg:px-8">
      <Link
        href="/cart"
        className="mb-6 inline-flex items-center gap-1 text-sm text-[var(--md-on-surface-variant)] hover:text-[var(--md-on-surface)]"
      >
        <ArrowLeft className="h-4 w-4" /> Back to Cart
      </Link>

      <h1 className="text-2xl font-bold text-[var(--md-on-surface)] mb-6">
        Checkout
      </h1>

      {/* Order Summary */}
      <div className="rounded-xl border border-[var(--md-outline-variant)] bg-[var(--md-surface)] p-4 mb-6">
        <h3 className="mb-3 font-medium text-[var(--md-on-surface)]">
          Order Summary
        </h3>
        <div className="space-y-2">
          {items.map((item) => (
            <div key={item.variant_id} className="flex justify-between text-sm">
              <span className="text-[var(--md-on-surface-variant)]">
                {item.name} × {item.quantity}
              </span>
              <span className="text-[var(--md-on-surface)]">
                KES {(item.price * item.quantity).toLocaleString()}
              </span>
            </div>
          ))}
          {coupon_discount > 0 && (
            <div className="flex justify-between text-sm border-t border-[var(--md-outline-variant)] pt-2">
              <span className="text-[var(--md-error)]">
                Discount ({coupon_code})
              </span>
              <span className="text-[var(--md-error)]">
                - KES {coupon_discount.toLocaleString()}
              </span>
            </div>
          )}
          <div className="flex justify-between font-bold border-t border-[var(--md-outline-variant)] pt-2">
            <span className="text-[var(--md-on-surface)]">Total</span>
            <span className="text-[var(--md-on-surface)]">
              KES {total.toLocaleString()}
            </span>
          </div>
        </div>
      </div>

      {/* Payment Form */}
      <div className="rounded-xl border border-[var(--md-outline-variant)] bg-[var(--md-surface)] p-6">
        <h3 className="mb-4 font-medium text-[var(--md-on-surface)]">
          M-Pesa Payment
        </h3>
        <p className="mb-4 text-sm text-[var(--md-on-surface-variant)]">
          Enter your M-Pesa phone number. You will receive an STK Push prompt
          to complete the payment.
        </p>

        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-[var(--md-on-surface-variant)]">
              Phone Number *
            </label>
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="0712345678"
              className="w-full rounded-lg border border-[var(--md-outline)] bg-[var(--md-surface-container)] px-4 py-3 text-sm focus:border-[var(--md-primary)] focus:outline-none"
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-[var(--md-on-surface-variant)]">
              Name (optional)
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your name"
              className="w-full rounded-lg border border-[var(--md-outline)] bg-[var(--md-surface-container)] px-4 py-3 text-sm focus:border-[var(--md-primary)] focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-[var(--md-on-surface-variant)]">
              Email (optional)
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full rounded-lg border border-[var(--md-outline)] bg-[var(--md-surface-container)] px-4 py-3 text-sm focus:border-[var(--md-primary)] focus:outline-none"
            />
          </div>
        </div>

        <button
          onClick={handleCheckout}
          disabled={!phone.trim()}
          className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl px-6 py-3 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          style={{ backgroundColor: "var(--color-primary)" }}
        >
          Pay KES {total.toLocaleString()} via M-Pesa
        </button>
      </div>
    </div>
  );
}
