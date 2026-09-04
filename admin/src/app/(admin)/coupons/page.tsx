"use client";

import { useState } from "react";
import { Plus, Ticket, Pencil, Trash2 } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { DataTable, TableSkeleton } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Dialog } from "@/components/ui/Dialog";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { StatCard } from "@/components/ui/StatCard";
import { formatDateTime } from "@/lib/utils";
import { useUIStore } from "@/stores/uiStore";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

interface ICoupon {
  id: string;
  code: string;
  description: string;
  discount_type: "percentage" | "fixed";
  discount_value: string;
  min_order_amount: string;
  max_discount_amount: string | null;
  max_uses: number | null;
  times_used: number;
  max_uses_per_customer: number | null;
  valid_from: string;
  valid_to: string | null;
  is_active: boolean;
  created_at: string;
}

const discountTypeOptions = [
  { value: "percentage", label: "Percentage (%)" },
  { value: "fixed", label: "Fixed amount (KES)" },
];

const couponSchema = z.object({
  code: z.string().min(2, "Code must be at least 2 characters").max(50),
  description: z.string().optional(),
  discount_type: z.enum(["percentage", "fixed"]),
  discount_value: z.string().min(1, "Discount value is required"),
  min_order_amount: z.string().optional(),
  max_discount_amount: z.string().optional(),
  max_uses: z.string().optional(),
  max_uses_per_customer: z.string().optional(),
  valid_from: z.string().optional(),
  valid_to: z.string().optional(),
});

type CouponFormData = z.infer<typeof couponSchema>;

function useCoupons() {
  return useQuery({
    queryKey: ["coupons"],
    queryFn: async () => {
      const { data } = await api.get("/coupons/?page_size=100");
      return (data?.data ?? data?.results ?? []) as ICoupon[];
    },
  });
}

function CouponActions({
  coupon,
  onEdit,
  onDelete,
  onToggle,
}: {
  coupon: ICoupon;
  onEdit: () => void;
  onDelete: () => void;
  onToggle: () => void;
}) {
  return (
    <div className="flex gap-1">
      <Button size="sm" variant="ghost" onClick={onToggle}>
        {coupon.is_active ? "Deactivate" : "Activate"}
      </Button>
      <Button size="sm" variant="ghost" onClick={onEdit}>
        <Pencil className="h-3.5 w-3.5" />
      </Button>
      <Button size="sm" variant="ghost" onClick={onDelete}>
        <Trash2 className="h-3.5 w-3.5 text-red-500" />
      </Button>
    </div>
  );
}

export default function CouponsPage() {
  const queryClient = useQueryClient();
  const { addToast } = useUIStore();
  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<ICoupon | null>(null);

  const { data: coupons = [], isLoading } = useCoupons();

  const form = useForm<CouponFormData>({
    resolver: zodResolver(couponSchema),
    defaultValues: {
      code: "",
      description: "",
      discount_type: "percentage",
      discount_value: "",
      min_order_amount: "",
      max_discount_amount: "",
      max_uses: "",
      max_uses_per_customer: "",
      valid_from: "",
      valid_to: "",
    },
  });

  const createMutation = useMutation({
    mutationFn: async (data: CouponFormData) => {
      const payload = {
        ...data,
        code: data.code.toUpperCase(),
        discount_value: parseFloat(data.discount_value),
        min_order_amount: data.min_order_amount ? parseFloat(data.min_order_amount) : 0,
        max_discount_amount: data.max_discount_amount ? parseFloat(data.max_discount_amount) : null,
        max_uses: data.max_uses ? parseInt(data.max_uses) : null,
        max_uses_per_customer: data.max_uses_per_customer ? parseInt(data.max_uses_per_customer) : null,
      };
      await api.post("/coupons/", payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["coupons"] });
      setShowCreate(false);
      form.reset();
      addToast({ type: "success", message: "Coupon created" });
    },
    onError: (err: any) => {
      addToast({ type: "error", message: err.response?.data?.errors?.[0]?.message || "Failed to create coupon" });
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, ...data }: Partial<CouponFormData> & { id: string }) => {
      const payload: Record<string, unknown> = {};
      if (data.code) payload.code = data.code.toUpperCase();
      if (data.description !== undefined) payload.description = data.description;
      if (data.discount_type) payload.discount_type = data.discount_type;
      if (data.discount_value) payload.discount_value = parseFloat(data.discount_value);
      if (data.min_order_amount !== undefined) payload.min_order_amount = data.min_order_amount ? parseFloat(data.min_order_amount) : 0;
      if (data.max_discount_amount !== undefined) payload.max_discount_amount = data.max_discount_amount ? parseFloat(data.max_discount_amount) : null;
      if (data.max_uses !== undefined) payload.max_uses = data.max_uses ? parseInt(data.max_uses) : null;
      if (data.valid_to !== undefined) payload.valid_to = data.valid_to || null;
      await api.patch(`/coupons/${id}/`, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["coupons"] });
      setEditing(null);
      addToast({ type: "success", message: "Coupon updated" });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/coupons/${id}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["coupons"] });
      addToast({ type: "success", message: "Coupon deleted" });
    },
  });

  const toggleActive = useMutation({
    mutationFn: async (coupon: ICoupon) => {
      await api.patch(`/coupons/${coupon.id}/`, { is_active: !coupon.is_active });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["coupons"] });
    },
  });

  const activeCoupons = coupons.filter((c) => c.is_active).length;
  const totalRedemptions = coupons.reduce((sum, c) => sum + (Number(c.times_used) || 0), 0);

  const columns = [
    {
      header: "Code",
      accessor: (coupon: ICoupon) => (
        <span className="font-mono font-bold text-sm">{coupon.code}</span>
      ),
    },
    {
      header: "Discount",
      accessor: (coupon: ICoupon) =>
        coupon.discount_type === "percentage"
          ? `${coupon.discount_value}%`
          : `KES ${coupon.discount_value}`,
    },
    {
      header: "Min Order",
      accessor: (coupon: ICoupon) =>
        parseFloat(coupon.min_order_amount) > 0 ? `KES ${coupon.min_order_amount}` : "—",
    },
    {
      header: "Uses",
      accessor: (coupon: ICoupon) => (
        <span>
          {coupon.times_used}
          {coupon.max_uses ? ` / ${coupon.max_uses}` : ""}
        </span>
      ),
    },
    {
      header: "Expires",
      accessor: (coupon: ICoupon) =>
        coupon.valid_to ? formatDateTime(coupon.valid_to) : "Never",
    },
    {
      header: "Status",
      accessor: (coupon: ICoupon) => (
        <Badge variant={coupon.is_active ? "success" : "default"}>
          {coupon.is_active ? "Active" : "Inactive"}
        </Badge>
      ),
    },
    {
      header: "",
      accessor: (coupon: ICoupon) => (
        <CouponActions
          coupon={coupon}
          onEdit={() => {
            setEditing(coupon);
            form.reset({
              code: coupon.code,
              description: coupon.description,
              discount_type: coupon.discount_type,
              discount_value: coupon.discount_value,
              min_order_amount: coupon.min_order_amount,
              max_discount_amount: coupon.max_discount_amount ?? "",
              max_uses: coupon.max_uses?.toString() ?? "",
              max_uses_per_customer: coupon.max_uses_per_customer?.toString() ?? "",
              valid_from: coupon.valid_from?.split("T")[0] ?? "",
              valid_to: coupon.valid_to?.split("T")[0] ?? "",
            });
          }}
          onDelete={() => {
            if (confirm("Delete this coupon?")) deleteMutation.mutate(coupon.id);
          }}
          onToggle={() => toggleActive.mutate(coupon)}
        />
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Coupons & Discounts</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Create and manage discount codes for your customers.
          </p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="h-4 w-4 mr-2" /> New Coupon
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard icon={<Ticket className="h-5 w-5" />} label="Active Coupons" value={activeCoupons} />
        <StatCard icon={<Ticket className="h-5 w-5" />} label="Total Coupons" value={coupons.length} />
        <StatCard icon={<Ticket className="h-5 w-5" />} label="Total Redemptions" value={totalRedemptions} />
      </div>

      {isLoading ? (
        <TableSkeleton rows={5} cols={6} />
      ) : (
        <DataTable columns={columns} data={coupons} keyAccessor={(c) => c.id} />
      )}

      {/* Create Dialog */}
      <Dialog open={showCreate} onClose={() => setShowCreate(false)} title="Create Coupon">
        <form onSubmit={form.handleSubmit((data) => createMutation.mutate(data))} className="space-y-4">
          <Input label="Code" {...form.register("code")} placeholder="e.g. SAVE20" />
          <Input label="Description" {...form.register("description")} placeholder="Internal note" />
          <Select
            label="Discount Type"
            options={discountTypeOptions}
            {...form.register("discount_type")}
          />
          <Input
            label={form.watch("discount_type") === "percentage" ? "Percentage (%)" : "Amount (KES)"}
            type="number"
            step="0.01"
            {...form.register("discount_value")}
          />
          <Input label="Min Order Amount (KES)" type="number" step="0.01" {...form.register("min_order_amount")} />
          {form.watch("discount_type") === "percentage" && (
            <Input label="Max Discount Cap (KES)" type="number" step="0.01" {...form.register("max_discount_amount")} />
          )}
          <Input label="Max Total Uses" type="number" {...form.register("max_uses")} />
          <div className="grid grid-cols-2 gap-3">
            <Input label="Valid From" type="date" {...form.register("valid_from")} />
            <Input label="Valid To" type="date" {...form.register("valid_to")} />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? "Creating..." : "Create Coupon"}
            </Button>
          </div>
        </form>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={!!editing} onClose={() => setEditing(null)} title="Edit Coupon">
        {editing && (
          <form onSubmit={form.handleSubmit((data) => updateMutation.mutate({ id: editing.id, ...data }))} className="space-y-4">
            <Input label="Code" {...form.register("code")} />
            <Input label="Description" {...form.register("description")} />
            <Select
              label="Discount Type"
              options={discountTypeOptions}
              {...form.register("discount_type")}
            />
            <Input
              label={form.watch("discount_type") === "percentage" ? "Percentage (%)" : "Amount (KES)"}
              type="number"
              step="0.01"
              {...form.register("discount_value")}
            />
            <Input label="Min Order Amount (KES)" type="number" step="0.01" {...form.register("min_order_amount")} />
            <Input label="Max Total Uses" type="number" {...form.register("max_uses")} />
            <Input label="Valid To" type="date" {...form.register("valid_to")} />
            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="ghost" onClick={() => setEditing(null)}>Cancel</Button>
              <Button type="submit" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? "Saving..." : "Save Changes"}
              </Button>
            </div>
          </form>
        )}
      </Dialog>
    </div>
  );
}
