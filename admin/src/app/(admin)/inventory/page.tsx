"use client";

import { useState } from "react";
import { Search, Package } from "lucide-react";
import { useInventory } from "@/hooks/useInventory";
import { DataTable, TableSkeleton } from "@/components/ui/DataTable";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Badge } from "@/components/ui/Badge";
import { StatCard } from "@/components/ui/StatCard";

export default function InventoryPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const { data: inventory, isLoading } = useInventory({
    search: search || undefined,
    status: statusFilter || undefined,
  });

  const items = inventory ?? [];
  const lowStock = items.filter((i) => i.status === "low_stock").length;
  const outOfStock = items.filter((i) => i.status === "out_of_stock").length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Inventory</h1>
        <p className="text-sm text-gray-500">Stock levels and management</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard
          label="Total Products"
          value={items.length}
          icon={<Package size={20} />}
        />
        <StatCard
          label="Low Stock"
          value={lowStock}
          icon={<Package size={20} />}
          change={lowStock > 0 ? "Needs attention" : undefined}
        />
        <StatCard
          label="Out of Stock"
          value={outOfStock}
          icon={<Package size={20} />}
        />
      </div>

      <div className="flex flex-col gap-4 sm:flex-row">
        <div className="relative flex-1">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
          />
          <Input
            placeholder="Search inventory..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select
          options={[
            { value: "", label: "All Status" },
            { value: "in_stock", label: "In Stock" },
            { value: "low_stock", label: "Low Stock" },
            { value: "out_of_stock", label: "Out of Stock" },
          ]}
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        />
      </div>

      {isLoading ? (
        <TableSkeleton rows={8} cols={5} />
      ) : (
        <DataTable
          columns={[
            { header: "Product", accessor: "product_name" },
            { header: "Variant", accessor: "variant_name" },
            { header: "SKU", accessor: "sku" },
            {
              header: "Stock",
              accessor: (item) => item.current_stock.toString(),
            },
            {
              header: "Status",
              accessor: (item) => (
                <Badge
                  variant={
                    item.status === "in_stock"
                      ? "success"
                      : item.status === "low_stock"
                        ? "warning"
                        : "danger"
                  }
                >
                  {item.status === "in_stock"
                    ? "In Stock"
                    : item.status === "low_stock"
                      ? "Low"
                      : "Out"}
                </Badge>
              ),
            },
          ]}
          data={items}
          emptyMessage="No inventory items found"
        />
      )}
    </div>
  );
}
