"use client";

import { useRouter } from "next/navigation";
import { ShoppingCart, BarChart3, LogOut } from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import { useDashboardStats } from "@/hooks/useDashboard";
import { StatCard, StatCardSkeleton } from "@/components/ui/StatCard";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { formatCurrency, formatTime } from "@/lib/utils";

export default function WaiterDashboardPage() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const { data: stats, isLoading } = useDashboardStats();

  const handleLogout = () => {
    clearAuth();
    router.push("/login/");
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-[var(--md-on-surface)]">
            Welcome, {user?.email?.split("@")[0] ?? "Waiter"}
          </h1>
          <p className="text-sm text-[var(--md-on-surface-variant)]">Today&apos;s shift</p>
        </div>
        <Button variant="ghost" onClick={handleLogout}>
          <LogOut size={16} />
        </Button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 gap-4">
          <StatCardSkeleton />
          <StatCardSkeleton />
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          <StatCard
            label="My Orders"
            value={stats?.today_transactions ?? 0}
            icon={<ShoppingCart size={20} />}
          />
          <StatCard
            label="My Revenue"
            value={formatCurrency(stats?.today_revenue ?? "0")}
            icon={<BarChart3 size={20} />}
          />
        </div>
      )}

      <Button
        onClick={() => router.push("/pos/")}
        className="w-full text-lg"
      >
        <ShoppingCart size={20} className="mr-2" />
        Take New Order
      </Button>

      <Card>
        <CardContent>
          <h2 className="mb-3 font-semibold text-[var(--md-on-surface)]">Recent Orders</h2>
          {stats?.recent_orders && stats.recent_orders.length > 0 ? (
            <div className="space-y-2">
              {stats.recent_orders.slice(0, 5).map((order) => (
                <div
                  key={order.id}
                  className="flex items-center justify-between rounded-xl border border-[var(--md-outline-variant)] p-3 transition-colors hover:bg-[var(--md-surface-variant)]"
                >
                  <div>
                    <p className="font-medium text-[var(--md-on-surface)]">#{order.order_reference}</p>
                    <p className="text-sm text-[var(--md-on-surface-variant)]">
                      {formatTime(order.created_at)}
                    </p>
                  </div>
                  <p className="font-semibold text-[var(--md-on-surface)]">
                    {formatCurrency(order.total)}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="py-4 text-center text-sm text-[var(--md-on-surface-variant)]">
              No orders yet today
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
