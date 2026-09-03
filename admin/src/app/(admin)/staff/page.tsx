"use client";

import { useState } from "react";
import { Plus, UserCog } from "lucide-react";
import { useStaff, useCreateStaff } from "@/hooks/useStaff";
import { DataTable, TableSkeleton } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Badge, StatusBadge } from "@/components/ui/Badge";
import { Dialog } from "@/components/ui/Dialog";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { StatCard } from "@/components/ui/StatCard";
import { formatDateTime } from "@/lib/utils";
import { useUIStore } from "@/stores/uiStore";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import type { IStaff, UserRole } from "@/types";

const roleVariant: Record<UserRole, "success" | "warning" | "info" | "default"> = {
  store_owner: "success",
  store_manager: "info",
  cashier: "warning",
  waiter: "default",
  platform_admin: "success",
};

const schema = z.object({
  email: z.string().email("Invalid email"),
  first_name: z.string().min(1, "First name is required"),
  last_name: z.string().min(1, "Last name is required"),
  role: z.string().min(1, "Role is required"),
  password: z.string().min(6, "Password must be at least 6 characters"),
});

type FormData = z.infer<typeof schema>;

export default function StaffPage() {
  const addToast = useUIStore((s) => s.addToast);
  const [showForm, setShowForm] = useState(false);

  const { data: staff, isLoading } = useStaff();
  const createStaff = useCreateStaff();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { role: "cashier" },
  });

  const onSubmit = async (data: FormData) => {
    await createStaff.mutateAsync({
      ...data,
      role: data.role as UserRole,
    });
    addToast({ type: "success", message: "Staff member added" });
    reset();
    setShowForm(false);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--md-on-surface)]">Staff</h1>
          <p className="text-sm text-[var(--md-on-surface-variant)]">Manage your team</p>
        </div>
        <Button onClick={() => setShowForm(true)}>
          <Plus size={16} className="mr-2" />
          Add Staff
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <StatCard
          label="Total Staff"
          value={staff?.meta?.count ?? 0}
          icon={<UserCog size={20} />}
        />
      </div>

      {isLoading ? (
        <TableSkeleton rows={5} cols={4} />
      ) : (
        <DataTable
          columns={[
            {
              header: "Name",
              accessor: (item) =>
                `${item.first_name} ${item.last_name}` || item.email,
            },
            { header: "Email", accessor: "email" },
            {
              header: "Role",
              accessor: (item) => (
                <Badge variant={roleVariant[item.role] ?? "default"}>
                  {item.role.replace("_", " ")}
                </Badge>
              ),
            },
            {
              header: "Status",
              accessor: (item) => <StatusBadge active={item.is_active} />,
            },
            {
              header: "Last Login",
              accessor: (item) =>
                item.last_login ? formatDateTime(item.last_login) : "\u2014",
            },
          ]}
          data={staff?.data ?? []}
          emptyMessage="No staff members found"
        />
      )}

      <Dialog
        open={showForm}
        onClose={() => setShowForm(false)}
        title="Add Staff Member"
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input
            label="Email"
            type="email"
            {...register("email")}
            error={errors.email?.message}
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="First Name"
              {...register("first_name")}
              error={errors.first_name?.message}
            />
            <Input
              label="Last Name"
              {...register("last_name")}
              error={errors.last_name?.message}
            />
          </div>
          <Select
            label="Role"
            options={[
              { value: "cashier", label: "Cashier" },
              { value: "waiter", label: "Waiter" },
              { value: "store_manager", label: "Manager" },
            ]}
            {...register("role")}
            error={errors.role?.message}
          />
          <Input
            label="Password"
            type="password"
            {...register("password")}
            error={errors.password?.message}
          />
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setShowForm(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={createStaff.isPending}>
              Add Staff
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
