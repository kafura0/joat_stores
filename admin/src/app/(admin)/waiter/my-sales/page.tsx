"use client";

import { useAuthStore } from "@/stores/authStore";
import { useDashboardStats } from "@/hooks/useDashboard";
import { StatCard, StatCardSkeleton } from "@/components/ui/StatCard";
import { Card, CardContent } from "@/components/ui/Card";
import { formatCurrency, formatTime } from "@/lib/utils";
import { BarChart3, ShoppingCart } from "lucide-react";

export default function MySalesPage() {
  const user = useAuthStore((s) => s.user);
  const { data: stats, isLoading } = useDashboardStats();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">My Sales</h1>
        <p className="text-sm text-gray-500">
          {user?.email?.split("@")[0]} &middot; Today&apos;s performance
        </p>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 gap-4">
          <StatCardSkeleton />
          <StatCardSkeleton />
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          <StatCard
            label="Orders Served"
            value={stats?.today_transactions ?? 0}
            icon={<ShoppingCart size={20} />}
          />
          <StatCard
            label="Revenue Generated"
            value={formatCurrency(stats?.today_revenue ?? "0")}
            icon={<BarChart3 size={20} />}
          />
        </div>
      )}

      <Card>
        <CardContent>
          <h2 className="mb-3 font-semibold">My Order History</h2>
          {stats?.recent_orders && stats.recent_orders.length > 0 ? (
            <div className="space-y-2">
              {stats.recent_orders.map((order) => (
                <div
                  key={order.id}
                  className="flex items-center justify-between rounded-lg border p-3"
                >
                  <div>
                    <p className="font-medium">#{order.order_reference}</p>
                    <p className="text-sm text-gray-500">
                      {formatTime(order.created_at)} &middot; {order.items?.length ?? 0} items
                    </p>
                  </div>
                  <p className="font-semibold">
                    {formatCurrency(order.total)}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="py-4 text-center text-sm text-gray-500">
              No orders served yet
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
