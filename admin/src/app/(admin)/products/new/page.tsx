"use client";

import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ArrowLeft } from "lucide-react";
import { useCreateProduct } from "@/hooks/useProducts";
import { useCategories } from "@/hooks/useCategories";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { useUIStore } from "@/stores/uiStore";

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  category_id: z.number().nullable(),
  description: z.string().optional(),
  is_available: z.boolean(),
});

type FormData = z.infer<typeof schema>;

export default function NewProductPage() {
  const router = useRouter();
  const addToast = useUIStore((s) => s.addToast);
  const { data: categories } = useCategories();
  const createProduct = useCreateProduct();

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: "",
      category_id: null,
      description: "",
      is_available: true,
    },
  });

  const categoryOptions = [
    { value: "", label: "No Category" },
    ...(categories?.data.map((c) => ({ value: c.id, label: c.name })) ?? []),
  ];

  const onSubmit = async (data: FormData) => {
    try {
      const product = await createProduct.mutateAsync({
        ...data,
        attribute_names: [],
      });
      addToast({ type: "success", message: "Product created" });
      router.push(`/products/${product.id}/`);
    } catch {
      addToast({ type: "error", message: "Failed to create product" });
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" onClick={() => router.back()}>
          <ArrowLeft size={16} />
        </Button>
        <div>
          <h1 className="text-2xl font-bold text-[var(--md-on-surface)]">New Product</h1>
          <p className="text-sm text-[var(--md-on-surface-variant)]">Add a new product to your catalog</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <h2 className="font-semibold text-[var(--md-on-surface)]">Product Details</h2>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <Input
              label="Product Name"
              {...register("name")}
              error={errors.name?.message}
              placeholder="e.g. Tusker Lager"
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
              placeholder="Optional description"
            />

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="is_available"
                {...register("is_available")}
                className="h-4 w-4 rounded border-[var(--md-outline)] accent-[var(--md-primary)]"
              />
              <label htmlFor="is_available" className="text-sm text-[var(--md-on-surface-variant)]">
                Active (available for sale)
              </label>
            </div>

            <div className="flex justify-end gap-2 pt-4">
              <Button
                type="button"
                variant="secondary"
                onClick={() => router.push("/products/")}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={createProduct.isPending}>
                {createProduct.isPending ? "Creating..." : "Create Product"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
