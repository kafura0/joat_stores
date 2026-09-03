"use client";

import { Store, Users, DollarSign, Activity } from "lucide-react";
import { usePlatformStores } from "@/hooks/usePlatform";
import { StatCard, StatCardSkeleton } from "@/components/ui/StatCard";
import { DataTable, TableSkeleton } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { formatDate } from "@/lib/utils";

export default function PlatformPage() {
  const { data: stores, isLoading } = usePlatformStores();

  const totalStores = stores?.meta?.count ?? 0;
  const activeStores = stores?.data?.filter((s) => s.is_active).length ?? 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--md-on-surface)]">
          JOAT STORES — Platform Overview
        </h1>
        <p className="text-sm text-[var(--md-on-surface-variant)]">Manage your SaaS platform</p>
      </div>

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
            value={totalStores}
            icon={<Store size={20} />}
          />
          <StatCard
            label="Active Stores"
            value={activeStores}
            icon={<Activity size={20} />}
          />
          <StatCard
            label="Total Users"
            value="\u2014"
            icon={<Users size={20} />}
          />
          <StatCard
            label="Platform Revenue"
            value="\u2014"
            icon={<DollarSign size={20} />}
          />
        </div>
      )}

      <div>
        <h2 className="mb-4 text-lg font-semibold text-[var(--md-on-surface)]">Stores</h2>
        {isLoading ? (
          <TableSkeleton rows={5} cols={4} />
        ) : (
          <DataTable
            columns={[
              { header: "Name", accessor: "name" },
              { header: "Slug", accessor: "slug" },
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
    </div>
  );
}
