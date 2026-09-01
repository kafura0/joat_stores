"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Search, Plus, Users } from "lucide-react";
import { useCustomers, useCreateCustomer } from "@/hooks/useCustomers";
import { DataTable, TableSkeleton } from "@/components/ui/DataTable";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Card, CardContent } from "@/components/ui/Card";
import { StatCard } from "@/components/ui/StatCard";
import { formatCurrency, formatDate } from "@/lib/utils";
import { useUIStore } from "@/stores/uiStore";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import type { ICustomer } from "@/types";

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().email().optional().or(z.literal("")),
  phone: z.string().min(1, "Phone is required"),
});

type FormData = z.infer<typeof schema>;

export default function CustomersPage() {
  const router = useRouter();
  const addToast = useUIStore((s) => s.addToast);
  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);

  const { data: customers, isLoading } = useCustomers({
    search: search || undefined,
  });
  const createCustomer = useCreateCustomer();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    await createCustomer.mutateAsync({
      ...data,
      email: data.email || undefined,
    });
    addToast({ type: "success", message: "Customer created" });
    reset();
    setShowForm(false);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Customers</h1>
          <p className="text-sm text-gray-500">Manage your customer base</p>
        </div>
        <Button onClick={() => setShowForm(true)}>
          <Plus size={16} className="mr-2" />
          Add Customer
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <StatCard
          label="Total Customers"
          value={customers?.meta?.count ?? 0}
          icon={<Users size={20} />}
        />
      </div>

      <div className="relative">
        <Search
          size={16}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
        />
        <Input
          placeholder="Search customers..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {isLoading ? (
        <TableSkeleton rows={8} cols={5} />
      ) : (
        <DataTable
          columns={[
            { header: "Name", accessor: "name" },
            { header: "Phone", accessor: "phone" },
            { header: "Email", accessor: "email" },
            {
              header: "Orders",
              accessor: (item) => item.total_orders.toString(),
            },
            {
              header: "Total Spent",
              accessor: (item) => formatCurrency(item.total_spent),
            },
            {
              header: "Joined",
              accessor: (item) => formatDate(item.created_at),
            },
          ]}
          data={customers?.data ?? []}
          onRowClick={(item) => router.push(`/customers/${item.id}/`)}
          emptyMessage="No customers found"
        />
      )}

      <Dialog open={showForm} onClose={() => setShowForm(false)} title="Add Customer">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input
            label="Name"
            {...register("name")}
            error={errors.name?.message}
          />
          <Input
            label="Phone"
            {...register("phone")}
            error={errors.phone?.message}
          />
          <Input
            label="Email (optional)"
            type="email"
            {...register("email")}
          />
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setShowForm(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={createCustomer.isPending}>
              Create
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
