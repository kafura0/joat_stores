"use client";

import { useState, useMemo } from "react";
import { Search, Users } from "lucide-react";
import { useStaff } from "@/hooks/useStaff";
import { Badge, StatusBadge } from "@/components/ui/Badge";
import { formatDateTime } from "@/lib/utils";
import type { UserRole } from "@/types";

const roleVariant: Record<UserRole, "success" | "warning" | "info" | "default"> = {
  platform_admin: "success",
  store_owner: "success",
  store_manager: "info",
  cashier: "warning",
  waiter: "default",
  kitchen: "info",
};

const roleLabels: Record<UserRole, string> = {
  platform_admin: "Platform Admin",
  store_owner: "Store Owner",
  store_manager: "Store Manager",
  cashier: "Cashier",
  waiter: "Waiter",
  kitchen: "Kitchen",
};

export default function PlatformUsersPage() {
  const { data: users, isLoading } = useStaff();
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("all");

  const allUsers = users?.data ?? [];

  const filtered = useMemo(() => {
    let result = allUsers;
    if (roleFilter !== "all") {
      result = result.filter((u) => u.role === roleFilter);
    }
    if (search) {
      const q = search.toLowerCase();
      result = result.filter(
        (u) =>
          u.email?.toLowerCase().includes(q) ||
          u.first_name?.toLowerCase().includes(q) ||
          u.last_name?.toLowerCase().includes(q)
      );
    }
    return result;
  }, [allUsers, search, roleFilter]);

  const stats = useMemo(() => {
    const byRole = allUsers.reduce(
      (acc, u) => {
        acc[u.role] = (acc[u.role] || 0) + 1;
        return acc;
      },
      {} as Record<string, number>
    );
    return {
      total: allUsers.length,
      active: allUsers.filter((u) => u.is_active).length,
      owners: byRole["store_owner"] ?? 0,
      managers: byRole["store_manager"] ?? 0,
    };
  }, [allUsers]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--md-on-surface)]">
            Users
          </h1>
          <p className="mt-1 text-sm text-[var(--md-on-surface-variant)]">
            All platform users across every store
          </p>
        </div>
      </div>

      {/* Stats */}
      {!isLoading && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MiniStat label="Total Users" value={stats.total} />
          <MiniStat label="Active" value={stats.active} />
          <MiniStat label="Store Owners" value={stats.owners} />
          <MiniStat label="Managers" value={stats.managers} />
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1 max-w-md">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--md-on-surface-variant)]"
          />
          <input
            type="text"
            placeholder="Search by name or email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-[var(--md-outline)] bg-[var(--md-surface)] py-3 pl-10 pr-4 text-sm text-[var(--md-on-surface)] placeholder:text-[var(--md-on-surface-variant)] focus:border-[var(--md-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--md-primary)]"
            style={{ minHeight: 48 }}
          />
        </div>
        <div className="flex gap-2 flex-wrap">
          {(["all", "platform_admin", "store_owner", "store_manager", "cashier", "waiter", "kitchen"] as const).map(
            (role) => (
              <button
                key={role}
                onClick={() => setRoleFilter(role)}
                className={`rounded-lg px-3 py-2 text-xs font-medium transition-all ${
                  roleFilter === role
                    ? "bg-[var(--md-primary)] text-white"
                    : "border border-[var(--md-outline)] bg-[var(--md-surface)] text-[var(--md-on-surface-variant)] hover:bg-[var(--md-surface-variant)]"
                }`}
                style={{ minHeight: 36 }}
              >
                {role === "all" ? "All" : roleLabels[role]}
              </button>
            )
          )}
        </div>
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
                    User
                  </th>
                  <th className="px-6 py-3 text-xs font-semibold uppercase tracking-wider text-[var(--md-on-surface-variant)]">
                    Role
                  </th>
                  <th className="px-6 py-3 text-xs font-semibold uppercase tracking-wider text-[var(--md-on-surface-variant)]">
                    Status
                  </th>
                  <th className="px-6 py-3 text-xs font-semibold uppercase tracking-wider text-[var(--md-on-surface-variant)]">
                    Last Login
                  </th>
                </tr>
              </thead>
              <tbody className="text-sm">
                {filtered.map((user) => (
                  <tr
                    key={user.id}
                    className="border-b border-[var(--md-outline-variant)]/30 transition-colors hover:bg-[var(--md-surface-variant)]/50"
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--md-primary-container)] text-sm font-bold text-[var(--md-on-primary-container)]">
                          {user.first_name?.[0]?.toUpperCase() ??
                            user.email[0].toUpperCase()}
                        </div>
                        <div>
                          <p className="font-medium text-[var(--md-on-surface)]">
                            {user.first_name || user.last_name
                              ? `${user.first_name} ${user.last_name}`.trim()
                              : user.email}
                          </p>
                          <p className="text-xs text-[var(--md-on-surface-variant)]">
                            {user.email}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <Badge variant={roleVariant[user.role] ?? "default"}>
                        {roleLabels[user.role] ?? user.role}
                      </Badge>
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge active={user.is_active} />
                    </td>
                    <td className="px-6 py-4 text-[var(--md-on-surface-variant)]">
                      {user.last_login ? formatDateTime(user.last_login) : "—"}
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td
                      colSpan={4}
                      className="px-6 py-12 text-center text-[var(--md-on-surface-variant)]"
                    >
                      {search || roleFilter !== "all"
                        ? "No users match your filters"
                        : "No users found"}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
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
