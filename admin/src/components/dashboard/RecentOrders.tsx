"use client";

import Link from "next/link";
import { formatCurrency, formatTime } from "@/lib/utils";
import { useDashboardStats } from "@/hooks/useDashboard";
import { Badge } from "@/components/ui/Badge";

const statusVariant: Record<string, "success" | "warning" | "danger" | "info"> = {
  completed: "success",
  confirmed: "info",
  pending: "warning",
  cancelled: "danger",
};

export function RecentOrders() {
  const { data: stats, isLoading } = useDashboardStats();

  if (isLoading) {
    return (
      <div className="glass-panel rounded-xl border border-[var(--md-outline-variant)] bg-[var(--md-surface-container)] p-6 backdrop-blur-md">
        <div className="mb-4 h-5 w-32 animate-pulse rounded bg-[var(--md-surface-variant)]" />
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="mb-3 h-10 animate-pulse rounded bg-[var(--md-surface-variant)]" />
        ))}
      </div>
    );
  }

  const orders = stats?.recent_orders ?? [];

  return (
    <div className="glass-panel rounded-xl border border-[var(--md-outline-variant)] bg-[var(--md-surface-container)] p-6 backdrop-blur-md">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="font-semibold text-[var(--md-on-surface)]">Recent Orders</h3>
        <Link href="/orders/" className="text-sm text-[var(--md-tertiary)] hover:underline">
          View all
        </Link>
      </div>
      {orders.length === 0 ? (
        <p className="py-8 text-center text-sm text-[var(--md-on-surface-variant)]">No orders yet</p>
      ) : (
        <div className="space-y-3">
          {orders.map((order) => (
            <Link
              key={order.id}
              href={`/orders/${order.id}/`}
              className="flex items-center justify-between rounded-xl border border-[var(--md-outline-variant)] p-3 transition-all duration-200 hover:bg-[var(--md-surface-variant)] hover:shadow-[var(--shadow-subtle)]"
            >
              <div>
                <p className="font-medium text-[var(--md-on-surface)]">#{order.order_reference}</p>
                <p className="text-sm text-[var(--md-on-surface-variant)]">
                  {formatTime(order.created_at)} &middot; {order.items?.length ?? 0} items
                </p>
              </div>
              <div className="text-right">
                <p className="font-semibold text-[var(--md-on-surface)]">{formatCurrency(order.total)}</p>
                <Badge variant={statusVariant[order.status] ?? "default"}>
                  {order.status}
                </Badge>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
