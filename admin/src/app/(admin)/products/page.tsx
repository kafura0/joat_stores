"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Search } from "lucide-react";
import { useProducts, useDeleteProduct } from "@/hooks/useProducts";
import { useCategories } from "@/hooks/useCategories";
import { DataTable, TableSkeleton } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Badge } from "@/components/ui/Badge";
import { Dialog } from "@/components/ui/Dialog";
import { formatCurrency } from "@/lib/utils";
import { useUIStore } from "@/stores/uiStore";
import type { IProduct } from "@/types";

export default function ProductsPage() {
  const router = useRouter();
  const addToast = useUIStore((s) => s.addToast);
  const [search, setSearch] = useState("");
  const [categoryId, setCategoryId] = useState<string>("");
  const [deleteId, setDeleteId] = useState<number | null>(null);

  const { data: products, isLoading } = useProducts({
    search: search || undefined,
    category_id: categoryId ? Number(categoryId) : undefined,
  });
  const { data: categories } = useCategories();
  const deleteProduct = useDeleteProduct();

  const categoryOptions = [
    { value: "", label: "All Categories" },
    ...(categories?.data.map((c) => ({ value: c.id, label: c.name })) ?? []),
  ];

  const handleDelete = async () => {
    if (!deleteId) return;
    await deleteProduct.mutateAsync(deleteId);
    addToast({ type: "success", message: "Product deleted" });
    setDeleteId(null);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--md-on-surface)]">Products</h1>
          <p className="text-sm text-[var(--md-on-surface-variant)]">Manage your product catalog</p>
        </div>
        <Button onClick={() => router.push("/products/new/")}>
          <Plus size={16} className="mr-2" />
          Add Product
        </Button>
      </div>

      <div className="flex flex-col gap-4 sm:flex-row">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--md-on-surface-variant)]" />
          <Input
            placeholder="Search products, SKUs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select
          options={categoryOptions}
          value={categoryId}
          onChange={(e) => setCategoryId(e.target.value)}
        />
      </div>

      {isLoading ? (
        <TableSkeleton rows={8} cols={5} />
      ) : (
        <DataTable
          columns={[
            { header: "Name", accessor: "name" },
            {
              header: "Category",
              accessor: (item) => item.category?.name ?? "—",
            },
            {
              header: "Price",
              accessor: (item) =>
                item.variants?.[0]
                  ? formatCurrency(item.variants[0].price)
                  : "—",
            },
            {
              header: "Stock",
              accessor: (item) =>
                item.variants?.[0]?.inventory_count?.toString() ?? "0",
            },
            {
              header: "Status",
              accessor: (item) => (
                <Badge variant={item.is_available ? "success" : "danger"}>
                  {item.is_available ? "Active" : "Inactive"}
                </Badge>
              ),
            },
            {
              header: "Actions",
              accessor: (item) => (
                <div className="flex gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      router.push(`/products/${item.id}/`);
                    }}
                  >
                    Edit
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeleteId(item.id);
                    }}
                  >
                    Delete
                  </Button>
                </div>
              ),
            },
          ]}
          data={products?.data ?? []}
          onRowClick={(item) => router.push(`/products/${item.id}/`)}
          emptyMessage="No products found"
        />
      )}

      <Dialog
        open={!!deleteId}
        onClose={() => setDeleteId(null)}
        title="Delete Product"
      >
        <p className="text-sm text-[var(--md-on-surface-variant)]">
          Are you sure you want to delete this product? This action cannot be
          undone.
        </p>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDeleteId(null)}>
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={handleDelete}
            disabled={deleteProduct.isPending}
          >
            Delete
          </Button>
        </div>
      </Dialog>
    </div>
  );
}
