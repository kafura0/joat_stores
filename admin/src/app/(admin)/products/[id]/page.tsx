"use client";

import { useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ArrowLeft } from "lucide-react";
import { useProduct, useUpdateProduct, useDeleteProduct } from "@/hooks/useProducts";
import { useCategories } from "@/hooks/useCategories";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { PageLoading } from "@/components/ui/LoadingSpinner";
import { useUIStore } from "@/stores/uiStore";

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  category_id: z.number().nullable(),
  description: z.string().optional(),
  is_available: z.boolean(),
});

type FormData = z.infer<typeof schema>;

export default function ProductDetailPage() {
  const router = useRouter();
  const params = useParams();
  const id = Number(params.id);
  const addToast = useUIStore((s) => s.addToast);

  const { data: product, isLoading } = useProduct(id);
  const { data: categories } = useCategories();
  const updateProduct = useUpdateProduct();
  const deleteProduct = useDeleteProduct();

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
  } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  // Initialize form when product loads
  if (product && !watch("name")) {
    setValue("name", product.name);
    setValue("category_id", product.category_id);
    setValue("description", product.description);
    setValue("is_available", product.is_available);
  }

  const categoryOptions = [
    { value: "", label: "No Category" },
    ...(categories?.data.map((c) => ({ value: c.id, label: c.name })) ?? []),
  ];

  const onSubmit = async (data: FormData) => {
    await updateProduct.mutateAsync({ id, ...data });
    addToast({ type: "success", message: "Product updated" });
    router.push("/products/");
  };

  const handleDelete = async () => {
    await deleteProduct.mutateAsync(id);
    addToast({ type: "success", message: "Product deleted" });
    router.push("/products/");
  };

  if (isLoading) return <PageLoading />;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" onClick={() => router.back()}>
          <ArrowLeft size={16} />
        </Button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Edit Product</h1>
          <p className="text-sm text-gray-500">{product?.name}</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <h2 className="font-semibold">Product Details</h2>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <Input
              label="Product Name"
              {...register("name")}
              error={errors.name?.message}
            />

            <Select
              label="Category"
              options={categoryOptions}
              value={watch("category_id") ?? ""}
              onChange={(e) =>
                setValue(
                  "category_id",
                  e.target.value ? Number(e.target.value) : null
                )
              }
            />

            <Input
              label="Description"
              {...register("description")}
            />

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="is_available"
                {...register("is_available")}
                className="h-4 w-4 rounded border-gray-300"
              />
              <label htmlFor="is_available" className="text-sm text-gray-700">
                Active (available for sale)
              </label>
            </div>

            <div className="flex justify-between pt-4">
              <Button
                type="button"
                variant="danger"
                onClick={handleDelete}
                disabled={deleteProduct.isPending}
              >
                Delete Product
              </Button>
              <Button type="submit" disabled={updateProduct.isPending}>
                Save Changes
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {product?.variants && product.variants.length > 0 && (
        <Card>
          <CardHeader>
            <h2 className="font-semibold">Variants</h2>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {product.variants.map((variant) => (
                <div
                  key={variant.id}
                  className="flex items-center justify-between rounded-lg border p-3"
                >
                  <div>
                    <p className="font-medium">
                      {Object.values(variant.attribute_values).join(" / ") ||
                        "Default"}
                    </p>
                    <p className="text-sm text-gray-500">
                      SKU: {variant.sku || "—"} &middot; Stock:{" "}
                      {variant.inventory_count}
                    </p>
                  </div>
                  <p className="font-semibold">
                    {new Intl.NumberFormat("en-KE", {
                      style: "currency",
                      currency: "KES",
                    }).format(parseFloat(variant.price))}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
