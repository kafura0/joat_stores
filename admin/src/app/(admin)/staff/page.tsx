"use client";

import { useState } from "react";
import { Plus, UserCog, Pencil, UserX } from "lucide-react";
import { useStaff, useCreateStaff, useUpdateStaff, useDeactivateStaff } from "@/hooks/useStaff";
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
  kitchen: "info",
  platform_admin: "success",
};

const roleOptions = [
  { value: "cashier", label: "Cashier" },
  { value: "waiter", label: "Waiter" },
  { value: "kitchen", label: "Kitchen" },
  { value: "store_manager", label: "Manager" },
];

const createSchema = z.object({
  email: z.string().email("Invalid email"),
  first_name: z.string().min(1, "First name is required"),
  last_name: z.string().min(1, "Last name is required"),
  role: z.string().min(1, "Role is required"),
  password: z.string().min(6, "Password must be at least 6 characters"),
});

const editSchema = z.object({
  email: z.string().email("Invalid email"),
  first_name: z.string().min(1, "First name is required"),
  last_name: z.string().min(1, "Last name is required"),
  role: z.string().min(1, "Role is required"),
});

type CreateFormData = z.infer<typeof createSchema>;
type EditFormData = z.infer<typeof editSchema>;

export default function StaffPage() {
  const addToast = useUIStore((s) => s.addToast);
  const [showCreate, setShowCreate] = useState(false);
  const [editStaff, setEditStaff] = useState<IStaff | null>(null);
  const [deactivateId, setDeactivateId] = useState<string | null>(null);

  const { data: staff, isLoading } = useStaff();
  const createStaff = useCreateStaff();
  const updateStaff = useUpdateStaff();
  const deactivateStaff = useDeactivateStaff();

  const createForm = useForm<CreateFormData>({
    resolver: zodResolver(createSchema),
    defaultValues: { role: "cashier" },
  });

  const editForm = useForm<EditFormData>({
    resolver: zodResolver(editSchema),
  });

  const handleCreate = async (data: CreateFormData) => {
    await createStaff.mutateAsync({
      ...data,
      role: data.role as UserRole,
    });
    addToast({ type: "success", message: "Staff member added" });
    createForm.reset();
    setShowCreate(false);
  };

  const handleEdit = async (data: EditFormData) => {
    if (!editStaff) return;
    await updateStaff.mutateAsync({
      id: editStaff.id,
      ...data,
      role: data.role as UserRole,
    });
    addToast({ type: "success", message: "Staff member updated" });
    setEditStaff(null);
  };

  const handleDeactivate = async () => {
    if (!deactivateId) return;
    await deactivateStaff.mutateAsync(deactivateId);
    addToast({ type: "success", message: "Staff member deactivated" });
    setDeactivateId(null);
  };

  const openEdit = (item: IStaff) => {
    setEditStaff(item);
    editForm.reset({
      email: item.email,
      first_name: item.first_name,
      last_name: item.last_name,
      role: item.role,
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--md-on-surface)]">Staff</h1>
          <p className="text-sm text-[var(--md-on-surface-variant)]">Manage your team</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
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
        <TableSkeleton rows={5} cols={5} />
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
              header: "Actions",
              accessor: (item) => (
                <div className="flex gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      openEdit(item);
                    }}
                  >
                    <Pencil size={14} />
                  </Button>
                  {item.is_active && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeactivateId(item.id);
                      }}
                    >
                      <UserX size={14} />
                    </Button>
                  )}
                </div>
              ),
            },
          ]}
          data={staff?.data ?? []}
          emptyMessage="No staff members found"
        />
      )}

      {/* Create Dialog */}
      <Dialog
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title="Add Staff Member"
      >
        <form onSubmit={createForm.handleSubmit(handleCreate)} className="space-y-4">
          <Input
            label="Email"
            type="email"
            {...createForm.register("email")}
            error={createForm.formState.errors.email?.message}
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="First Name"
              {...createForm.register("first_name")}
              error={createForm.formState.errors.first_name?.message}
            />
            <Input
              label="Last Name"
              {...createForm.register("last_name")}
              error={createForm.formState.errors.last_name?.message}
            />
          </div>
          <Select
            label="Role"
            options={roleOptions}
            {...createForm.register("role")}
            error={createForm.formState.errors.role?.message}
          />
          <Input
            label="Password"
            type="password"
            {...createForm.register("password")}
            error={createForm.formState.errors.password?.message}
          />
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setShowCreate(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={createStaff.isPending}>
              Add Staff
            </Button>
          </div>
        </form>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog
        open={!!editStaff}
        onClose={() => setEditStaff(null)}
        title="Edit Staff Member"
      >
        <form onSubmit={editForm.handleSubmit(handleEdit)} className="space-y-4">
          <Input
            label="Email"
            type="email"
            {...editForm.register("email")}
            error={editForm.formState.errors.email?.message}
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="First Name"
              {...editForm.register("first_name")}
              error={editForm.formState.errors.first_name?.message}
            />
            <Input
              label="Last Name"
              {...editForm.register("last_name")}
              error={editForm.formState.errors.last_name?.message}
            />
          </div>
          <Select
            label="Role"
            options={roleOptions}
            {...editForm.register("role")}
            error={editForm.formState.errors.role?.message}
          />
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setEditStaff(null)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={updateStaff.isPending}>
              Save Changes
            </Button>
          </div>
        </form>
      </Dialog>

      {/* Deactivate Dialog */}
      <Dialog
        open={!!deactivateId}
        onClose={() => setDeactivateId(null)}
        title="Deactivate Staff Member"
      >
        <p className="text-sm text-[var(--md-on-surface-variant)]">
          Are you sure you want to deactivate this staff member? They will no
          longer be able to log in.
        </p>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDeactivateId(null)}>
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={handleDeactivate}
            disabled={deactivateStaff.isPending}
          >
            Deactivate
          </Button>
        </div>
      </Dialog>
    </div>
  );
}
