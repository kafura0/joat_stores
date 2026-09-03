"use client";

import { useState } from "react";
import { useCartStore } from "@/stores/cartStore";
import { useCheckout } from "@/hooks/useCart";
import { formatCurrency } from "@/lib/utils";
import { Dialog } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { useUIStore } from "@/stores/uiStore";

interface PaymentModalProps {
  open: boolean;
  onClose: () => void;
}

export function PaymentModal({ open, onClose }: PaymentModalProps) {
  const { total: getTotal, payment_method, setPaymentMethod, clearCart } =
    useCartStore();
  const checkout = useCheckout();
  const addToast = useUIStore((s) => s.addToast);
  const [cashReceived, setCashReceived] = useState("");

  const change =
    payment_method === "cash"
      ? Math.max(
          0,
          parseFloat(cashReceived || "0") - parseFloat(getTotal())
        )
      : 0;

  const handlePayment = async () => {
    try {
      await checkout.mutateAsync({ payment_method });
      clearCart();
      addToast({ type: "success", message: "Payment successful!" });
      setCashReceived("");
      onClose();
    } catch {
      addToast({ type: "error", message: "Payment failed. Please try again." });
    }
  };

  return (
    <Dialog open={open} onClose={onClose} title="Complete Payment">
      <div className="space-y-4">
        <div className="text-center">
          <p className="text-sm text-[var(--md-on-surface-variant)]">Total Due</p>
          <p className="text-3xl font-bold text-[var(--md-on-surface)]">{formatCurrency(getTotal())}</p>
        </div>

        <div className="grid grid-cols-3 gap-2">
          {(["cash", "mpesa", "card"] as const).map((method) => (
            <button
              key={method}
              onClick={() => setPaymentMethod(method)}
              className={`rounded-xl border-2 p-4 text-center font-medium transition-all ${
                payment_method === method
                  ? "border-[var(--md-primary)] bg-[var(--md-primary-container)] text-[var(--md-on-primary-container)] shadow-[var(--shadow-sm)]"
                  : "border-[var(--md-outline-variant)] text-[var(--md-on-surface-variant)] hover:border-[var(--md-outline)] hover:bg-[var(--md-surface-variant)]"
              }`}
              style={{ minHeight: 48 }}
            >
              {method === "cash"
                ? "Cash"
                : method === "mpesa"
                  ? "M-Pesa"
                  : "Card"}
            </button>
          ))}
        </div>

        {payment_method === "cash" && (
          <div>
            <label className="mb-1 block text-sm font-medium text-[var(--md-on-surface-variant)]">
              Cash Received
            </label>
            <input
              type="number"
              value={cashReceived}
              onChange={(e) => setCashReceived(e.target.value)}
              className="block w-full rounded-xl border border-[var(--md-outline)] bg-[var(--md-surface)] px-4 py-3 text-lg text-[var(--md-on-surface)] placeholder-[var(--md-on-surface-variant)] focus:border-[var(--md-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--md-primary)]"
              placeholder="0.00"
              style={{ minHeight: 48 }}
            />
            {change > 0 && (
              <p className="mt-1 text-sm text-[var(--md-success)]">
                Change: {formatCurrency(change)}
              </p>
            )}
          </div>
        )}

        <Button
          onClick={handlePayment}
          disabled={checkout.isPending}
          className="w-full bg-gradient-to-r from-[var(--md-success)] to-emerald-600 text-white hover:opacity-90 text-lg"
        >
          {checkout.isPending ? "Processing..." : "Confirm Payment"}
        </Button>
      </div>
    </Dialog>
  );
}
