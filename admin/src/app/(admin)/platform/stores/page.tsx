"use client";

import { useState, useMemo } from "react";
import { Search, Store, Activity, AlertTriangle, Clock } from "lucide-react";
import { usePlatformStores, useUpdateStoreStatus } from "@/hooks/usePlatform";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Input } from "@/components/ui/Input";
import { StatCardSkeleton } from "@/components/ui/StatCard";
import { formatDate } from "@/lib/utils";
import { useUIStore } from "@/stores/uiStore";

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

export default function PlatformStoresPage() {
  const { data: stores, isLoading } = usePlatformStores();
  const updateStatus = useUpdateStoreStatus();
  const addToast = useUIStore((s) => s.addToast);
  const [search, setSearch] = useState("");
  const [actionStore, setActionStore] = useState<{
    id: string;
    name: string;
    status: string;
    tenant_type: string;
    slug: string;
  } | null>(null);

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
    const dormant = allStores.filter((s) => s.status === "inactive").length;
    return { total: allStores.length, active, trial, suspended, dormant };
  }, [allStores]);

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
          <StatCard
            label="Total Stores"
            value={stats.total}
            icon={<Store size={20} />}
            changeType="neutral"
          />
          <StatCard
            label="Active"
            value={stats.active}
            icon={<Activity size={20} />}
            changeType="up"
          />
          <StatCard
            label="On Trial"
            value={stats.trial}
            icon={<Clock size={20} />}
            changeType="neutral"
          />
          <StatCard
            label="Suspended"
            value={stats.suspended}
            icon={<AlertTriangle size={20} />}
            changeType={stats.suspended > 0 ? "down" : "up"}
          />
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
                      {search ? "No stores match your search" : "No stores found"}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Manage Dialog */}
      <Dialog
        open={!!actionStore}
        onClose={() => setActionStore(null)}
        title={`Manage ${actionStore?.name ?? ""}`}
      >
        {actionStore && (
          <div className="space-y-4">
            {/* Store Info */}
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

            {/* Status */}
            <div className="flex items-center gap-3">
              <span className="text-sm text-[var(--md-on-surface-variant)]">
                Current status:
              </span>
              <Badge variant={statusVariant[actionStore.status] ?? "default"}>
                {actionStore.status}
              </Badge>
            </div>

            {/* Actions */}
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

/* --- Stat Card (inline to avoid import issues) --- */
function StatCard({
  label,
  value,
  icon,
  changeType,
}: {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  changeType?: "up" | "down" | "neutral";
}) {
  return (
    <div className="premium-card rounded-xl border border-[var(--md-outline-variant)] bg-[var(--md-surface-container)] p-6 backdrop-blur-md transition-all duration-200 hover:shadow-[var(--shadow-elevated)] hover:-translate-y-0.5">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-[var(--md-on-surface-variant)]">
          {label}
        </p>
        <div className="text-[var(--md-tertiary)]">{icon}</div>
      </div>
      <p className="mt-2 text-2xl font-semibold text-[var(--md-on-surface)]">
        {value}
      </p>
    </div>
  );
}
