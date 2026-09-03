"use client";

import { useRouter, useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { useOrder } from "@/hooks/useOrders";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { PageLoading } from "@/components/ui/LoadingSpinner";
import { formatCurrency, formatDateTime } from "@/lib/utils";
import type { OrderStatus } from "@/types";

const statusVariant: Record<OrderStatus, "success" | "warning" | "danger" | "info"> = {
  completed: "success",
  confirmed: "info",
  pending: "warning",
  cancelled: "danger",
  fulfilled: "success",
};

export default function OrderDetailPage() {
  const router = useRouter();
  const params = useParams();
  const id = params.id as string;

  const { data: order, isLoading } = useOrder(id);

  if (isLoading) return <PageLoading />;
  if (!order) return <div className="p-8 text-center text-[var(--md-on-surface-variant)]">Order not found</div>;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" onClick={() => router.back()}>
          <ArrowLeft size={16} />
        </Button>
        <div>
          <h1 className="text-2xl font-bold text-[var(--md-on-surface)]">
            Order #{order.order_reference}
          </h1>
          <p className="text-sm text-[var(--md-on-surface-variant)]">
            {formatDateTime(order.created_at)}
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-[var(--md-on-surface)]">Order Details</h2>
            <Badge variant={statusVariant[order.status]}>{order.status}</Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {order.items.map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between border-b border-[var(--md-outline-variant)] pb-3"
              >
                <div>
                  <p className="font-medium text-[var(--md-on-surface)]">{item.product_name}</p>
                  <p className="text-sm text-[var(--md-on-surface-variant)]">
                    {formatCurrency(item.unit_price)} x {item.quantity}
                  </p>
                </div>
                <p className="font-semibold text-[var(--md-on-surface)]">{formatCurrency(item.total)}</p>
              </div>
            ))}

            <div className="space-y-2 pt-4">
              <div className="flex justify-between text-sm">
                <span className="text-[var(--md-on-surface-variant)]">Subtotal</span>
                <span className="text-[var(--md-on-surface)]">{formatCurrency(order.subtotal)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-[var(--md-on-surface-variant)]">Tax</span>
                <span className="text-[var(--md-on-surface)]">{formatCurrency(order.tax_amount)}</span>
              </div>
              <div className="flex justify-between border-t border-[var(--md-outline-variant)] pt-2 text-lg font-bold">
                <span className="text-[var(--md-on-surface)]">Total</span>
                <span className="text-[var(--md-on-surface)]">{formatCurrency(order.total)}</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-[var(--md-on-surface-variant)]">Payment Method</p>
              <p className="font-medium text-[var(--md-on-surface)]">{order.payment_method.toUpperCase()}</p>
            </div>
            <div>
              <p className="text-[var(--md-on-surface-variant)]">Payment Status</p>
              <p className="font-medium text-[var(--md-on-surface)]">{order.payment_status}</p>
            </div>
            {order.served_by && (
              <div>
                <p className="text-[var(--md-on-surface-variant)]">Served By</p>
                <p className="font-medium text-[var(--md-on-surface)]">{order.served_by}</p>
              </div>
            )}
            {order.notes && (
              <div className="col-span-2">
                <p className="text-[var(--md-on-surface-variant)]">Notes</p>
                <p className="font-medium text-[var(--md-on-surface)]">{order.notes}</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
