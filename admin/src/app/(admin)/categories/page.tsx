"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, ArrowLeft } from "lucide-react";
import { useCategories, useCreateCategory, useDeleteCategory } from "@/hooks/useCategories";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { DataTable, TableSkeleton } from "@/components/ui/DataTable";
import { Dialog } from "@/components/ui/Dialog";
import { Card, CardContent } from "@/components/ui/Card";
import { useUIStore } from "@/stores/uiStore";
import type { ICategory } from "@/types";

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().optional(),
});

type FormData = z.infer<typeof schema>;

export default function CategoriesPage() {
  const router = useRouter();
  const addToast = useUIStore((s) => s.addToast);
  const [showForm, setShowForm] = useState(false);
  const [deleteId, setDeleteId] = useState<number | null>(null);

  const { data: categories, isLoading } = useCategories();
  const createCategory = useCreateCategory();
  const deleteCategory = useDeleteCategory();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    await createCategory.mutateAsync(data);
    addToast({ type: "success", message: "Category created" });
    reset();
    setShowForm(false);
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    await deleteCategory.mutateAsync(deleteId);
    addToast({ type: "success", message: "Category deleted" });
    setDeleteId(null);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={() => router.back()}>
            <ArrowLeft size={16} />
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-[var(--md-on-surface)]">Categories</h1>
            <p className="text-sm text-[var(--md-on-surface-variant)]">Organize your products</p>
          </div>
        </div>
        <Button onClick={() => setShowForm(true)}>
          <Plus size={16} className="mr-2" />
          Add Category
        </Button>
      </div>

      {showForm && (
        <Card>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <Input
                label="Category Name"
                {...register("name")}
                error={errors.name?.message}
              />
              <Input label="Description (optional)" {...register("description")} />
              <div className="flex justify-end gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => setShowForm(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={createCategory.isPending}>
                  Create
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <TableSkeleton rows={5} cols={3} />
      ) : (
        <DataTable
          columns={[
            { header: "Name", accessor: "name" },
            { header: "Description", accessor: "description" },
            {
              header: "Products",
              accessor: (item) => item.product_count?.toString() ?? "0",
            },
            {
              header: "Actions",
              accessor: (item) => (
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
              ),
            },
          ]}
          data={categories?.data ?? []}
          emptyMessage="No categories yet"
        />
      )}

      <Dialog
        open={!!deleteId}
        onClose={() => setDeleteId(null)}
        title="Delete Category"
      >
        <p className="text-sm text-[var(--md-on-surface-variant)]">
          Are you sure you want to delete this category?
        </p>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDeleteId(null)}>
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={handleDelete}
            disabled={deleteCategory.isPending}
          >
            Delete
          </Button>
        </div>
      </Dialog>
    </div>
  );
}
