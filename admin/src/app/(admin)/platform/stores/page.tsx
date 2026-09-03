"use client";

import { usePlatformStores } from "@/hooks/usePlatform";
import { DataTable, TableSkeleton } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { formatDate } from "@/lib/utils";

export default function PlatformStoresPage() {
  const { data: stores, isLoading } = usePlatformStores();

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
            { header: "Domain", accessor: "domain" },
            { header: "Type", accessor: "tenant_type" },
            {
              header: "Status",
              accessor: (item) => (
                <Badge variant={item.is_active ? "success" : "danger"}>
                  {item.is_active ? "Active" : "Inactive"}
                </Badge>
              ),
            },
            {
              header: "Created",
              accessor: (item) => formatDate(item.created_at),
            },
          ]}
          data={stores?.data ?? []}
          emptyMessage="No stores found"
        />
      )}
    </div>
  );
}
