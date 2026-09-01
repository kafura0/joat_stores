"use client";

import { formatCurrency } from "@/lib/utils";
import { useDashboardStats } from "@/hooks/useDashboard";
import { TrendingUp } from "lucide-react";

export function TopProducts() {
  const { data: stats, isLoading } = useDashboardStats();

  if (isLoading) {
    return (
      <div className="rounded-lg border bg-white p-6">
        <div className="mb-4 h-5 w-32 animate-pulse rounded bg-gray-200" />
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="mb-3 h-8 animate-pulse rounded bg-gray-100" />
        ))}
      </div>
    );
  }

  const products = stats?.top_products ?? [];

  return (
    <div className="rounded-lg border bg-white p-6">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="font-semibold text-gray-900">Top Products</h3>
        <TrendingUp size={16} className="text-gray-400" />
      </div>
      {products.length === 0 ? (
        <p className="py-8 text-center text-sm text-gray-500">
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
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-gray-100 text-xs font-medium text-gray-600">
                  {index + 1}
                </span>
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    {product.product_name}
                  </p>
                  <p className="text-xs text-gray-500">
                    {product.quantity_sold} sold
                  </p>
                </div>
              </div>
              <p className="text-sm font-semibold text-gray-900">
                {formatCurrency(product.revenue)}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
