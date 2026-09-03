"use client";

import { formatCurrency } from "@/lib/utils";
import { useDashboardStats } from "@/hooks/useDashboard";
import { TrendingUp } from "lucide-react";

export function TopProducts() {
  const { data: stats, isLoading } = useDashboardStats();

  if (isLoading) {
    return (
      <div className="glass-panel rounded-xl border border-[var(--md-outline-variant)] bg-[var(--md-surface-container)] p-6 backdrop-blur-md">
        <div className="mb-4 h-5 w-32 animate-pulse rounded bg-[var(--md-surface-variant)]" />
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="mb-3 h-8 animate-pulse rounded bg-[var(--md-surface-variant)]" />
        ))}
      </div>
    );
  }

  const products = stats?.top_products ?? [];

  return (
    <div className="glass-panel rounded-xl border border-[var(--md-outline-variant)] bg-[var(--md-surface-container)] p-6 backdrop-blur-md">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="font-semibold text-[var(--md-on-surface)]">Top Products</h3>
        <TrendingUp size={16} className="text-[var(--md-on-surface-variant)]" />
      </div>
      {products.length === 0 ? (
        <p className="py-8 text-center text-sm text-[var(--md-on-surface-variant)]">
          No sales data yet
        </p>
      ) : (
        <div className="space-y-3">
          {products.map((product, index) => (
            <div
              key={product.product_name}
              className="flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--md-primary-container)] text-xs font-medium text-[var(--md-on-primary-container)]">
                  {index + 1}
                </span>
                <div>
                  <p className="text-sm font-medium text-[var(--md-on-surface)]">
                    {product.product_name}
                  </p>
                  <p className="text-xs text-[var(--md-on-surface-variant)]">
                    {product.quantity_sold} sold
                  </p>
                </div>
              </div>
              <p className="text-sm font-semibold text-[var(--md-on-surface)]">
                {formatCurrency(product.revenue)}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
