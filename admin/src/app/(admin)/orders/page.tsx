"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";
import { useOrders } from "@/hooks/useOrders";
import { DataTable, TableSkeleton } from "@/components/ui/DataTable";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Badge } from "@/components/ui/Badge";
import { Card, CardContent } from "@/components/ui/Card";
import { formatCurrency, formatDateTime } from "@/lib/utils";
import type { IOrder, OrderStatus, PaymentMethod } from "@/types";

const statusVariant: Record<OrderStatus, "success" | "warning" | "danger" | "info"> = {
  completed: "success",
  confirmed: "info",
  pending: "warning",
  cancelled: "danger",
  fulfilled: "success",
};

export default function OrdersPage() {
  const router = useRouter();
  const [statusFilter, setStatusFilter] = useState("");
  const [paymentFilter, setPaymentFilter] = useState("");

  const { data: orders, isLoading } = useOrders({
    status: statusFilter || undefined,
    payment_method: paymentFilter || undefined,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Orders</h1>
        <p className="text-sm text-gray-500">Transaction history</p>
      </div>

      <div className="flex flex-col gap-4 sm:flex-row">
        <Select
          options={[
            { value: "", label: "All Statuses" },
            { value: "pending", label: "Pending" },
            { value: "confirmed", label: "Confirmed" },
            { value: "completed", label: "Completed" },
            { value: "cancelled", label: "Cancelled" },
          ]}
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        />
        <Select
          options={[
            { value: "", label: "All Payments" },
            { value: "cash", label: "Cash" },
            { value: "mpesa", label: "M-Pesa" },
            { value: "card", label: "Card" },
          ]}
          value={paymentFilter}
          onChange={(e) => setPaymentFilter(e.target.value)}
        />
      </div>

      {isLoading ? (
        <TableSkeleton rows={10} cols={6} />
      ) : (
        <DataTable
          columns={[
            {
              header: "Receipt",
              accessor: (item) => (
                <span className="font-medium">#{item.order_reference}</span>
              ),
            },
            {
              header: "Date",
              accessor: (item) => formatDateTime(item.created_at),
            },
            {
              header: "Items",
              accessor: (item) => item.items?.length?.toString() ?? "0",
            },
            {
              header: "Total",
              accessor: (item) => (
                <span className="font-semibold">
                  {formatCurrency(item.total)}
                </span>
              ),
            },
            {
              header: "Payment",
              accessor: (item) => (
                <Badge
                  variant={
                    item.payment_method === "mpesa"
                      ? "info"
                      : item.payment_method === "card"
                        ? "success"
                        : "default"
                  }
                >
                  {item.payment_method.toUpperCase()}
                </Badge>
              ),
            },
            {
              header: "Status",
              accessor: (item) => (
                <Badge variant={statusVariant[item.status]}>
                  {item.status}
                </Badge>
              ),
            },
          ]}
          data={orders?.data ?? []}
          onRowClick={(item) => router.push(`/orders/${item.id}/`)}
          emptyMessage="No orders found"
        />
      )}
    </div>
  );
}
