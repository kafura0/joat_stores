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
  const { total, payment_method, setPaymentMethod, clearCart } =
    useCartStore();
  const checkout = useCheckout();
  const addToast = useUIStore((s) => s.addToast);
  const [cashReceived, setCashReceived] = useState("");

  const change =
    payment_method === "cash"
      ? Math.max(0, parseFloat(cashReceived || "0") - parseFloat(total))
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
          <p className="text-sm text-gray-500">Total Due</p>
          <p className="text-3xl font-bold">{formatCurrency(total)}</p>
        </div>

        <div className="grid grid-cols-3 gap-2">
          {(["cash", "mpesa", "card"] as const).map((method) => (
            <button
              key={method}
              onClick={() => setPaymentMethod(method)}
              className={`rounded-lg border-2 p-4 text-center font-medium transition ${
                payment_method === method
                  ? "border-blue-500 bg-blue-50 text-blue-700"
                  : "border-gray-200 hover:border-gray-300"
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
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Cash Received
            </label>
            <input
              type="number"
              value={cashReceived}
              onChange={(e) => setCashReceived(e.target.value)}
              className="block w-full rounded-lg border px-4 py-3 text-lg"
              placeholder="0.00"
              style={{ minHeight: 48 }}
            />
            {change > 0 && (
              <p className="mt-1 text-sm text-green-600">
                Change: {formatCurrency(change)}
              </p>
            )}
          </div>
        )}

        <Button
          onClick={handlePayment}
          disabled={checkout.isPending}
          className="w-full text-lg"
        >
          {checkout.isPending ? "Processing..." : "Confirm Payment"}
        </Button>
      </div>
    </Dialog>
  );
}
