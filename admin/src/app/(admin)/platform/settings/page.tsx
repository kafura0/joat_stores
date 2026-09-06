"use client";

import { useState } from "react";
import { CreditCard, Settings, Plus, Pencil, Trash2 } from "lucide-react";
import { usePlans, useCreatePlan } from "@/hooks/usePlatform";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Dialog } from "@/components/ui/Dialog";
import { Input } from "@/components/ui/Input";
import { StatCardSkeleton } from "@/components/ui/StatCard";
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
  const [editingPlan, setEditingPlan] = useState<{
    id: number;
    name: string;
    slug: string;
    price_kes: string;
    max_staff: number;
    max_products: number;
    monthly_order_limit: number;
    is_public: boolean;
  } | null>(null);
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
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--md-on-surface)]">
            Platform Settings
          </h1>
          <p className="mt-1 text-sm text-[var(--md-on-surface-variant)]">
            Configure subscription plans and platform defaults
          </p>
        </div>
        <Button onClick={() => setShowCreatePlan(true)}>
          <Plus size={16} className="mr-2" />
          Add Plan
        </Button>
      </div>

      {/* Subscription Plans */}
      <div className="premium-card overflow-hidden rounded-2xl border border-[var(--md-outline-variant)] bg-[var(--md-surface-container)] backdrop-blur-sm">
        <div className="flex items-center gap-3 border-b border-[var(--md-outline-variant)] bg-[var(--md-surface-container)]/50 px-6 py-4">
          <div className="rounded-lg bg-[var(--md-primary-container)] p-2">
            <CreditCard size={20} className="text-[var(--md-primary)]" />
          </div>
          <h3 className="text-lg font-bold text-[var(--md-on-surface)]">
            Subscription Plans
          </h3>
        </div>

        {isLoading ? (
          <div className="space-y-3 p-6">
            {Array.from({ length: 3 }).map((_, i) => (
              <div
                key={i}
                className="h-20 animate-pulse rounded-xl bg-[var(--md-surface-variant)]"
              />
            ))}
          </div>
        ) : plans && plans.length > 0 ? (
          <div className="divide-y divide-[var(--md-outline-variant)]">
            {plans.map((plan) => (
              <div
                key={plan.id}
                className="flex items-center justify-between px-6 py-4 transition-colors hover:bg-[var(--md-surface-variant)]/50"
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
                      {plan.is_public && <Badge variant="info">Public</Badge>}
                    </div>
                    <p className="mt-0.5 text-xs text-[var(--md-on-surface-variant)]">
                      {formatCurrency(plan.price_kes)}/mo ·{" "}
                      {plan.max_staff} staff · {plan.max_products} products ·{" "}
                      {plan.monthly_order_limit} orders/mo
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setEditingPlan(plan)}
                    className="rounded-lg p-2 text-[var(--md-on-surface-variant)] hover:bg-[var(--md-surface-variant)] hover:text-[var(--md-on-surface)]"
                    style={{ minHeight: 40, minWidth: 40 }}
                    aria-label={`Edit ${plan.name}`}
                  >
                    <Pencil size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="px-6 py-12 text-center">
            <CreditCard
              size={40}
              className="mx-auto mb-3 text-[var(--md-on-surface-variant)]/30"
            />
            <p className="text-sm text-[var(--md-on-surface-variant)]">
              No plans configured yet
            </p>
          </div>
        )}
      </div>

      {/* Platform Configuration */}
      <div className="premium-card overflow-hidden rounded-2xl border border-[var(--md-outline-variant)] bg-[var(--md-surface-container)] backdrop-blur-sm">
        <div className="flex items-center gap-3 border-b border-[var(--md-outline-variant)] bg-[var(--md-surface-container)]/50 px-6 py-4">
          <div className="rounded-lg bg-[var(--md-tertiary-container)] p-2">
            <Settings size={20} className="text-[var(--md-tertiary)]" />
          </div>
          <h3 className="text-lg font-bold text-[var(--md-on-surface)]">
            Platform Defaults
          </h3>
        </div>
        <div className="grid grid-cols-1 gap-4 p-6 sm:grid-cols-3">
          <ConfigItem label="Currency" value="KES" />
          <ConfigItem label="Tax Rate" value="16%" />
          <ConfigItem label="Timezone" value="Africa/Nairobi" />
        </div>
      </div>

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
            <label
              htmlFor="is_public"
              className="text-sm text-[var(--md-on-surface-variant)]"
            >
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

      {/* Edit Plan Dialog */}
      <Dialog
        open={!!editingPlan}
        onClose={() => setEditingPlan(null)}
        title={`Edit ${editingPlan?.name ?? ""}`}
      >
        {editingPlan && (
          <div className="space-y-4">
            <div className="rounded-xl border border-[var(--md-outline-variant)] bg-[var(--md-surface-variant)] p-4">
              <p className="text-sm text-[var(--md-on-surface-variant)]">
                Plan editing is coming soon. Currently you can create new plans.
              </p>
            </div>
            <div className="flex justify-end">
              <Button variant="secondary" onClick={() => setEditingPlan(null)}>
                Close
              </Button>
            </div>
          </div>
        )}
      </Dialog>
    </div>
  );
}

function ConfigItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-[var(--md-outline-variant)] bg-[var(--md-surface-variant)] p-4">
      <p className="text-xs font-semibold uppercase tracking-wider text-[var(--md-on-surface-variant)]">
        {label}
      </p>
      <p className="mt-1 text-lg font-semibold text-[var(--md-on-surface)]">
        {value}
      </p>
    </div>
  );
}
