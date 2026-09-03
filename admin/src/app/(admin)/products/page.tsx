"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { Plus, Search, Upload, Download } from "lucide-react";
import { useProducts, useDeleteProduct, useImportProducts, useUpdateProduct } from "@/hooks/useProducts";
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
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [search, setSearch] = useState("");
  const [categoryId, setCategoryId] = useState<string>("");
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingName, setEditingName] = useState("");
  const [editingPrice, setEditingPrice] = useState("");
  const [showImport, setShowImport] = useState(false);
  const [importResult, setImportResult] = useState<{ created: number; errors: Array<{ row: number; error: string }> } | null>(null);

  const { data: products, isLoading } = useProducts({
    search: search || undefined,
    category_id: categoryId ? Number(categoryId) : undefined,
  });
  const { data: categories } = useCategories();
  const deleteProduct = useDeleteProduct();
  const importProducts = useImportProducts();
  const updateProduct = useUpdateProduct();

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

  const handleInlineEdit = async (id: number) => {
    if (!editingName.trim()) return;
    try {
      await updateProduct.mutateAsync({
        id,
        name: editingName,
      });
      addToast({ type: "success", message: "Product updated" });
      setEditingId(null);
    } catch {
      addToast({ type: "error", message: "Failed to update product" });
    }
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const result = await importProducts.mutateAsync(file);
      setImportResult(result);
      addToast({
        type: result.errors.length > 0 ? "info" : "success",
        message: `Imported ${result.created} products${result.errors.length > 0 ? ` with ${result.errors.length} errors` : ""}`,
      });
    } catch {
      addToast({ type: "error", message: "Failed to import products" });
    }
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const downloadTemplate = () => {
    const csv = "name,price,category,stock,sku,description\nTusker Lager,350,Beers,100,TK-001,Popular Kenyan lager\nCaptain Morgan,800,Spirits,50,CM-001,Spiced rum";
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "product_template.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--md-on-surface)]">Products</h1>
          <p className="text-sm text-[var(--md-on-surface-variant)]">Manage your product catalog</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setShowImport(true)}>
            <Upload size={16} className="mr-2" />
            Import CSV
          </Button>
          <Button onClick={() => router.push("/products/new/")}>
            <Plus size={16} className="mr-2" />
            Add Product
          </Button>
        </div>
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
            {
              header: "Name",
              accessor: (item) => (
                editingId === item.id ? (
                  <Input
                    value={editingName}
                    onChange={(e) => setEditingName(e.target.value)}
                    onBlur={() => handleInlineEdit(item.id)}
                    onKeyDown={(e) => e.key === "Enter" && handleInlineEdit(item.id)}
                    className="h-8"
                    autoFocus
                  />
                ) : (
                  <span
                    className="cursor-pointer hover:underline"
                    onClick={(e) => {
                      e.stopPropagation();
                      setEditingId(item.id);
                      setEditingName(item.name);
                    }}
                  >
                    {item.name}
                  </span>
                )
              ),
            },
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

      {/* Delete Dialog */}
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

      {/* Import Dialog */}
      <Dialog
        open={showImport}
        onClose={() => { setShowImport(false); setImportResult(null); }}
        title="Import Products from CSV"
      >
        <div className="space-y-4">
          <p className="text-sm text-[var(--md-on-surface-variant)]">
            Upload a CSV file with columns: name, price, category, stock, sku, description
          </p>

          <div className="flex gap-2">
            <Button variant="secondary" onClick={downloadTemplate}>
              <Download size={16} className="mr-2" />
              Download Template
            </Button>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            onChange={handleImport}
            className="hidden"
          />
          <Button onClick={() => fileInputRef.current?.click()} disabled={importProducts.isPending}>
            {importProducts.isPending ? "Importing..." : "Choose CSV File"}
          </Button>

          {importResult && (
            <div className="rounded-xl border border-[var(--md-outline-variant)] bg-[var(--md-surface-variant)] p-4">
              <p className="font-medium text-[var(--md-on-surface)]">
                Imported {importResult.created} products
              </p>
              {importResult.errors.length > 0 && (
                <div className="mt-2">
                  <p className="text-sm text-[var(--md-error)]">
                    {importResult.errors.length} rows had errors:
                  </p>
                  <ul className="mt-1 text-xs text-[var(--md-on-surface-variant)]">
                    {importResult.errors.slice(0, 5).map((err, i) => (
                      <li key={i}>Row {err.row}: {err.error}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </Dialog>
    </div>
  );
}
