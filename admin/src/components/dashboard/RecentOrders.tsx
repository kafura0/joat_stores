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
      <div className="rounded-lg border bg-white p-6">
        <div className="mb-4 h-5 w-32 animate-pulse rounded bg-gray-200" />
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="mb-3 h-10 animate-pulse rounded bg-gray-100" />
        ))}
      </div>
    );
  }

  const orders = stats?.recent_orders ?? [];

  return (
    <div className="rounded-lg border bg-white p-6">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="font-semibold text-gray-900">Recent Orders</h3>
        <Link href="/orders/" className="text-sm text-blue-600 hover:underline">
          View all
        </Link>
      </div>
      {orders.length === 0 ? (
        <p className="py-8 text-center text-sm text-gray-500">No orders yet</p>
      ) : (
        <div className="space-y-3">
          {orders.map((order) => (
            <Link
              key={order.id}
              href={`/orders/${order.id}/`}
              className="flex items-center justify-between rounded-lg border p-3 transition hover:bg-gray-50"
            >
              <div>
                <p className="font-medium">#{order.order_reference}</p>
                <p className="text-sm text-gray-500">
                  {formatTime(order.created_at)} &middot; {order.items?.length ?? 0} items
                </p>
              </div>
              <div className="text-right">
                <p className="font-semibold">{formatCurrency(order.total)}</p>
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
