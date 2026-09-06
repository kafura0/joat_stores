"use client";

import { useState, useMemo } from "react";
import { Search, Plus } from "lucide-react";
import {
  usePlatformStores,
  useCreateStore,
  useUpdateStoreStatus,
} from "@/hooks/usePlatform";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { StatCardSkeleton } from "@/components/ui/StatCard";
import { formatDate } from "@/lib/utils";
import { useUIStore } from "@/stores/uiStore";
import { useAuthStore } from "@/stores/authStore";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import type { IOnboarding } from "@/hooks/usePlatform";

const statusVariant: Record<string, "success" | "warning" | "danger" | "info"> = {
  active: "success",
  trial: "info",
  suspended: "danger",
  inactive: "warning",
};

const typeBadge: Record<string, string> = {
  retail: "bg-[var(--md-tertiary-container)] text-[var(--md-on-tertiary-container)]",
  restaurant: "bg-[var(--md-warning-container)] text-[var(--md-warning)]",
  bar: "bg-[var(--md-primary-container)] text-[var(--md-on-primary-container)]",
  contracting: "bg-[var(--md-success-container)] text-[var(--md-success)]",
};

const storeSchema = z.object({
  name: z.string().min(1, "Store name is required"),
  domain: z.string().min(1, "Domain is required"),
  tenant_type: z.string().min(1, "Store type is required"),
  owner_email: z.string().email("Invalid email"),
});

type StoreFormData = z.infer<typeof storeSchema>;

export default function PlatformStoresPage() {
  const { data: stores, isLoading } = usePlatformStores();
  const updateStatus = useUpdateStoreStatus();
  const createStore = useCreateStore();
  const addToast = useUIStore((s) => s.addToast);
  const user = useAuthStore((s) => s.user);
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [onboarding, setOnboarding] = useState<IOnboarding | null>(null);
  const [onboardingStoreName, setOnboardingStoreName] = useState("");
  const [actionStore, setActionStore] = useState<{
    id: string;
    name: string;
    status: string;
    tenant_type: string;
    slug: string;
  } | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<StoreFormData>({
    resolver: zodResolver(storeSchema),
    defaultValues: { tenant_type: "retail" },
  });

  const allStores = stores?.data ?? [];

  const filtered = useMemo(() => {
    if (!search) return allStores;
    const q = search.toLowerCase();
    return allStores.filter(
      (s) =>
        s.name.toLowerCase().includes(q) ||
        s.slug?.toLowerCase().includes(q) ||
        s.tenant_type?.toLowerCase().includes(q) ||
        s.status?.toLowerCase().includes(q)
    );
  }, [allStores, search]);

  const stats = useMemo(() => {
    const active = allStores.filter((s) => s.status === "active").length;
    const trial = allStores.filter((s) => s.status === "trial").length;
    const suspended = allStores.filter((s) => s.status === "suspended").length;
    return { total: allStores.length, active, trial, suspended };
  }, [allStores]);

  const handleCreate = async (data: StoreFormData) => {
    try {
      const result = await createStore.mutateAsync({
        ...data,
        domain: data.domain.toLowerCase().replace(/[^a-z0-9.-]/g, ""),
      });
      addToast({ type: "success", message: "Store created successfully" });
      reset();
      setShowCreate(false);
      if (result.onboarding) {
        setOnboarding(result.onboarding);
        setOnboardingStoreName(result.name);
      }
    } catch {
      addToast({ type: "error", message: "Failed to create store" });
    }
  };

  const handleStatusUpdate = async (newStatus: string) => {
    if (!actionStore) return;
    try {
      await updateStatus.mutateAsync({ id: actionStore.id, status: newStatus });
      addToast({
        type: "success",
        message: `${actionStore.name} ${newStatus === "suspended" ? "suspended" : "activated"}`,
      });
      setActionStore(null);
    } catch {
      addToast({ type: "error", message: "Failed to update store status" });
    }
  };

  const isPlatformAdmin = user?.role === "platform_admin";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--md-on-surface)]">
            Stores
          </h1>
          <p className="mt-1 text-sm text-[var(--md-on-surface-variant)]">
            Manage all registered stores across your platform
          </p>
        </div>
        {isPlatformAdmin && (
          <Button onClick={() => setShowCreate(true)}>
            <Plus size={16} className="mr-2" />
            Add Store
          </Button>
        )}
      </div>

      {/* Stats */}
      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <StatCardSkeleton key={i} />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MiniStat label="Total" value={stats.total} />
          <MiniStat label="Active" value={stats.active} />
          <MiniStat label="On Trial" value={stats.trial} />
          <MiniStat label="Suspended" value={stats.suspended} />
        </div>
      )}

      {/* Search */}
      <div className="relative max-w-md">
        <Search
          size={16}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--md-on-surface-variant)]"
        />
        <input
          type="text"
          placeholder="Search stores..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-lg border border-[var(--md-outline)] bg-[var(--md-surface)] py-3 pl-10 pr-4 text-sm text-[var(--md-on-surface)] placeholder:text-[var(--md-on-surface-variant)] focus:border-[var(--md-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--md-primary)]"
          style={{ minHeight: 48 }}
        />
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className="h-16 animate-pulse rounded-xl bg-[var(--md-surface-container)]"
            />
          ))}
        </div>
      ) : (
        <div className="premium-card overflow-hidden rounded-2xl border border-[var(--md-outline-variant)] bg-[var(--md-surface-container)] backdrop-blur-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="border-b border-[var(--md-outline-variant)] bg-[var(--md-surface-container-high)]/50">
                <tr>
                  <th className="px-6 py-3 text-xs font-semibold uppercase tracking-wider text-[var(--md-on-surface-variant)]">
                    Store
                  </th>
                  <th className="px-6 py-3 text-xs font-semibold uppercase tracking-wider text-[var(--md-on-surface-variant)]">
                    Type
                  </th>
                  <th className="px-6 py-3 text-xs font-semibold uppercase tracking-wider text-[var(--md-on-surface-variant)]">
                    Status
                  </th>
                  <th className="px-6 py-3 text-xs font-semibold uppercase tracking-wider text-[var(--md-on-surface-variant)]">
                    Created
                  </th>
                  <th className="px-6 py-3 text-xs font-semibold uppercase tracking-wider text-[var(--md-on-surface-variant)]">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="text-sm">
                {filtered.map((store) => (
                  <tr
                    key={store.id}
                    className="border-b border-[var(--md-outline-variant)]/30 transition-colors hover:bg-[var(--md-surface-variant)]/50"
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--md-primary-container)] text-sm font-bold text-[var(--md-on-primary-container)]">
                          {store.name[0]?.toUpperCase() ?? "S"}
                        </div>
                        <div>
                          <p className="font-medium text-[var(--md-on-surface)]">
                            {store.name}
                          </p>
                          <p className="text-xs text-[var(--md-on-surface-variant)]">
                            {store.slug}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${
                          typeBadge[store.tenant_type] ?? "bg-[var(--md-surface-variant)] text-[var(--md-on-surface-variant)]"
                        }`}
                      >
                        {store.tenant_type}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <Badge variant={statusVariant[store.status] ?? "default"}>
                        {store.status}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 text-[var(--md-on-surface-variant)]">
                      {store.created_at ? formatDate(store.created_at) : "—"}
                    </td>
                    <td className="px-6 py-4">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          setActionStore({
                            id: store.id,
                            name: store.name,
                            status: store.status,
                            tenant_type: store.tenant_type,
                            slug: store.slug,
                          })
                        }
                      >
                        Manage
                      </Button>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td
                      colSpan={5}
                      className="px-6 py-12 text-center text-[var(--md-on-surface-variant)]"
                    >
                      {search
                        ? "No stores match your search"
                        : "No stores yet. Click 'Add Store' to create one."}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Create Store Dialog */}
      <Dialog
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title="Create New Store"
      >
        <form onSubmit={handleSubmit(handleCreate)} className="space-y-4">
          <Input
            label="Store Name"
            {...register("name")}
            error={errors.name?.message}
            placeholder="e.g. Mama's Supermarket"
          />
          <Input
            label="Domain"
            {...register("domain")}
            error={errors.domain?.message}
            placeholder="e.g. mamas.ke"
          />
          <Select
            label="Store Type"
            options={[
              { value: "retail", label: "Retail" },
              { value: "restaurant", label: "Restaurant" },
              { value: "bar", label: "Bar / Nightclub" },
              { value: "contracting", label: "Contracting" },
            ]}
            {...register("tenant_type")}
            error={errors.tenant_type?.message}
          />
          <Input
            label="Owner Email"
            type="email"
            {...register("owner_email")}
            error={errors.owner_email?.message}
            placeholder="owner@example.com"
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setShowCreate(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={createStore.isPending}>
              {createStore.isPending ? "Creating..." : "Create Store"}
            </Button>
          </div>
        </form>
      </Dialog>

      {/* Onboarding Success Dialog */}
      <Dialog
        open={!!onboarding}
        onClose={() => setOnboarding(null)}
        title="Store Created Successfully!"
      >
        {onboarding && (
          <div className="space-y-4">
            <div className="rounded-xl border border-[var(--md-success)]/20 bg-[var(--md-success-container)] p-4 text-center">
              <p className="text-sm font-medium text-[var(--md-success)]">
                {onboardingStoreName} is now live!
              </p>
            </div>
            <div className="rounded-xl border border-[var(--md-outline-variant)] bg-[var(--md-surface-variant)] p-4">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-[var(--md-on-surface-variant)]">
                Owner Credentials
              </p>
              <p className="text-sm text-[var(--md-on-surface)]">
                Email: <span className="font-medium">{onboarding.owner_email}</span>
              </p>
              <p className="text-sm text-[var(--md-on-surface)]">
                Password:{" "}
                <span className="rounded bg-[var(--md-primary-container)] px-2 py-0.5 font-mono text-xs font-bold text-[var(--md-on-primary-container)]">
                  {onboarding.temporary_password}
                </span>
              </p>
            </div>
            <Button onClick={() => setOnboarding(null)} className="w-full">
              Done
            </Button>
          </div>
        )}
      </Dialog>

      {/* Manage Dialog */}
      <Dialog
        open={!!actionStore}
        onClose={() => setActionStore(null)}
        title={`Manage ${actionStore?.name ?? ""}`}
      >
        {actionStore && (
          <div className="space-y-4">
            <div className="rounded-xl border border-[var(--md-outline-variant)] bg-[var(--md-surface-variant)] p-4">
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[var(--md-primary-container)] text-lg font-bold text-[var(--md-on-primary-container)]">
                  {actionStore.name[0]?.toUpperCase() ?? "S"}
                </div>
                <div>
                  <p className="font-semibold text-[var(--md-on-surface)]">
                    {actionStore.name}
                  </p>
                  <p className="text-xs text-[var(--md-on-surface-variant)]">
                    {actionStore.slug} · {actionStore.tenant_type}
                  </p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-sm text-[var(--md-on-surface-variant)]">
                Current status:
              </span>
              <Badge variant={statusVariant[actionStore.status] ?? "default"}>
                {actionStore.status}
              </Badge>
            </div>
            <div className="flex gap-2">
              {actionStore.status !== "active" && (
                <Button onClick={() => handleStatusUpdate("active")}>
                  Activate
                </Button>
              )}
              {actionStore.status !== "suspended" && (
                <Button
                  variant="danger"
                  onClick={() => handleStatusUpdate("suspended")}
                >
                  Suspend
                </Button>
              )}
              <Button variant="secondary" onClick={() => setActionStore(null)}>
                Cancel
              </Button>
            </div>
          </div>
        )}
      </Dialog>
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="premium-card rounded-xl border border-[var(--md-outline-variant)] bg-[var(--md-surface-container)] p-4 backdrop-blur-md">
      <p className="text-xs font-medium text-[var(--md-on-surface-variant)]">
        {label}
      </p>
      <p className="mt-1 text-xl font-semibold text-[var(--md-on-surface)]">
        {value}
      </p>
    </div>
  );
}
