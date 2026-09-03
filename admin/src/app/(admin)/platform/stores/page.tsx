"use client";

import { useState } from "react";
import { usePlatformStores, useUpdateStoreStatus } from "@/hooks/usePlatform";
import { DataTable, TableSkeleton } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { formatDate } from "@/lib/utils";
import { useUIStore } from "@/stores/uiStore";

const statusVariant: Record<string, "success" | "warning" | "danger" | "info"> = {
  active: "success",
  trial: "info",
  suspended: "danger",
  inactive: "warning",
};

export default function PlatformStoresPage() {
  const { data: stores, isLoading } = usePlatformStores();
  const updateStatus = useUpdateStoreStatus();
  const addToast = useUIStore((s) => s.addToast);
  const [actionStore, setActionStore] = useState<{
    id: string;
    name: string;
    status: string;
  } | null>(null);

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
      <div>
        <h1 className="text-2xl font-bold text-[var(--md-on-surface)]">Stores</h1>
        <p className="text-sm text-[var(--md-on-surface-variant)]">All registered stores</p>
      </div>

      {isLoading ? (
        <TableSkeleton rows={10} cols={5} />
      ) : (
        <DataTable
          columns={[
            { header: "Name", accessor: "name" },
            { header: "Slug", accessor: "slug" },
            { header: "Type", accessor: "tenant_type" },
            {
              header: "Status",
              accessor: (item) => (
                <Badge variant={statusVariant[item.status] ?? "default"}>
                  {item.status}
                </Badge>
              ),
            },
            {
              header: "Created",
              accessor: (item) => formatDate(item.created_at),
            },
            {
              header: "Actions",
              accessor: (item) => (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    setActionStore({
                      id: item.id,
                      name: item.name,
                      status: item.status,
                    });
                  }}
                >
                  Manage
                </Button>
              ),
            },
          ]}
          data={stores?.data ?? []}
          emptyMessage="No stores found"
        />
      )}

      {/* Store Action Dialog */}
      <Dialog
        open={!!actionStore}
        onClose={() => setActionStore(null)}
        title={`Manage ${actionStore?.name ?? ""}`}
      >
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <span className="text-sm text-[var(--md-on-surface-variant)]">
              Current status:
            </span>
            <Badge variant={statusVariant[actionStore?.status ?? ""] ?? "default"}>
              {actionStore?.status}
            </Badge>
          </div>
          <div className="flex gap-2">
            {actionStore?.status !== "active" && (
              <Button onClick={() => handleStatusUpdate("active")}>
                Activate
              </Button>
            )}
            {actionStore?.status !== "suspended" && (
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
      </Dialog>
    </div>
  );
}
