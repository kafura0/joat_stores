"use client";

import { StatCard, StatCardSkeleton } from "@/components/ui/StatCard";
import {
  DollarSign,
  ShoppingCart,
  TrendingUp,
  Package,
  AlertTriangle,
  Users,
} from "lucide-react";
import { formatCurrency } from "@/lib/utils";
import { useDashboardStats } from "@/hooks/useDashboard";

export function StatsGrid() {
  const { data: stats, isLoading } = useDashboardStats();

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <StatCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <StatCard
        label="Today's Revenue"
        value={formatCurrency(stats?.today_revenue ?? "0")}
        icon={<DollarSign size={20} />}
      />
      <StatCard
        label="Today's Orders"
        value={stats?.today_transactions ?? 0}
        icon={<ShoppingCart size={20} />}
      />
      <StatCard
        label="Avg Order Value"
        value={formatCurrency(stats?.today_avg_order ?? "0")}
        icon={<TrendingUp size={20} />}
      />
      <StatCard
        label="Total Products"
        value={stats?.total_products ?? 0}
        icon={<Package size={20} />}
      />
      <StatCard
        label="Low Stock Alerts"
        value={stats?.low_stock_count ?? 0}
        icon={<AlertTriangle size={20} />}
        change={
          (stats?.low_stock_count ?? 0) > 0
            ? `${stats?.low_stock_count} items need restocking`
            : undefined
        }
      />
      <StatCard
        label="Active Customers"
        value={stats?.active_customers ?? 0}
        icon={<Users size={20} />}
      />
    </div>
  );
}
