"use client";

import { useState } from "react";
import { usePlans, useCreatePlan } from "@/hooks/usePlatform";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Dialog } from "@/components/ui/Dialog";
import { Input } from "@/components/ui/Input";
import { useUIStore } from "@/stores/uiStore";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { formatCurrency } from "@/lib/utils";

const planSchema = z.object({
  name: z.string().min(1, "Plan name is required"),
  slug: z.string().min(1, "Slug is required"),
  price_kes: z.string().min(1, "Price is required"),
  monthly_order_limit: z.number().min(0),
  max_staff: z.number().min(1),
  max_products: z.number().min(1),
  is_public: z.boolean(),
});

type PlanFormData = z.infer<typeof planSchema>;

export default function PlatformSettingsPage() {
  const [showCreatePlan, setShowCreatePlan] = useState(false);
  const addToast = useUIStore((s) => s.addToast);
  const { data: plans, isLoading } = usePlans();
  const createPlan = useCreatePlan();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<PlanFormData>({
    resolver: zodResolver(planSchema),
    defaultValues: {
      price_kes: "0",
      monthly_order_limit: 100,
      max_staff: 3,
      max_products: 50,
      is_public: true,
    },
  });

  const onSubmit = async (data: PlanFormData) => {
    try {
      await createPlan.mutateAsync({
        ...data,
        price_kes: data.price_kes,
        monthly_order_limit: Number(data.monthly_order_limit),
        max_staff: Number(data.max_staff),
        max_products: Number(data.max_products),
      });
      addToast({ type: "success", message: "Plan created" });
      reset();
      setShowCreatePlan(false);
    } catch {
      addToast({ type: "error", message: "Failed to create plan" });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--md-on-surface)]">
            Platform Settings
          </h1>
          <p className="text-sm text-[var(--md-on-surface-variant)]">
            Configure platform-wide settings and plans
          </p>
        </div>
        <Button onClick={() => setShowCreatePlan(true)}>Add Plan</Button>
      </div>

      {/* Subscription Plans */}
      <Card>
        <CardHeader>
          <h2 className="font-semibold text-[var(--md-on-surface)]">
            Subscription Plans
          </h2>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="h-20 animate-pulse rounded-xl bg-[var(--md-surface-variant)]" />
              ))}
            </div>
          ) : plans && plans.length > 0 ? (
            <div className="space-y-3">
              {plans.map((plan) => (
                <div
                  key={plan.id}
                  className="flex items-center justify-between rounded-xl border border-[var(--md-outline-variant)] p-4 transition-colors hover:bg-[var(--md-surface-variant)]"
                >
                  <div className="flex items-center gap-4">
                    <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[var(--md-primary-container)] text-sm font-bold text-[var(--md-on-primary-container)]">
                      {plan.name[0]}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="font-semibold text-[var(--md-on-surface)]">
                          {plan.name}
                        </p>
                        <Badge variant={plan.is_active ? "success" : "danger"}>
                          {plan.is_active ? "Active" : "Inactive"}
                        </Badge>
                        {plan.is_public && (
                          <Badge variant="info">Public</Badge>
                        )}
                      </div>
                      <p className="mt-0.5 text-xs text-[var(--md-on-surface-variant)]">
                        {formatCurrency(plan.price_kes)}/mo &middot;{" "}
                        {plan.max_staff} staff &middot; {plan.max_products}{" "}
                        products &middot; {plan.monthly_order_limit} orders/mo
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="py-8 text-center text-sm text-[var(--md-on-surface-variant)]">
              No plans configured yet
            </p>
          )}
        </CardContent>
      </Card>

      {/* Platform Configuration */}
      <Card>
        <CardHeader>
          <h2 className="font-semibold text-[var(--md-on-surface)]">
            Platform Configuration
          </h2>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-[var(--md-on-surface-variant)]">
            Default currency: KES &middot; Tax rate: 16% &middot; Timezone: Africa/Nairobi
          </p>
        </CardContent>
      </Card>

      {/* Create Plan Dialog */}
      <Dialog
        open={showCreatePlan}
        onClose={() => setShowCreatePlan(false)}
        title="Create New Plan"
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input
            label="Plan Name"
            {...register("name")}
            error={errors.name?.message}
            placeholder="e.g. Growth"
          />
          <Input
            label="Slug"
            {...register("slug")}
            error={errors.slug?.message}
            placeholder="e.g. growth"
          />
          <Input
            label="Monthly Price (KES)"
            {...register("price_kes")}
            error={errors.price_kes?.message}
            placeholder="e.g. 2500"
          />
          <div className="grid grid-cols-3 gap-4">
            <Input
              label="Max Staff"
              type="number"
              {...register("max_staff", { valueAsNumber: true })}
              error={errors.max_staff?.message}
            />
            <Input
              label="Max Products"
              type="number"
              {...register("max_products", { valueAsNumber: true })}
              error={errors.max_products?.message}
            />
            <Input
              label="Order Limit/mo"
              type="number"
              {...register("monthly_order_limit", { valueAsNumber: true })}
              error={errors.monthly_order_limit?.message}
            />
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is_public"
              {...register("is_public")}
              className="h-4 w-4 rounded border-[var(--md-outline)] accent-[var(--md-primary)]"
            />
            <label htmlFor="is_public" className="text-sm text-[var(--md-on-surface-variant)]">
              Public (visible to all stores)
            </label>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setShowCreatePlan(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={createPlan.isPending}>
              {createPlan.isPending ? "Creating..." : "Create Plan"}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
