"use client";

import { useStaff } from "@/hooks/useStaff";
import { DataTable, TableSkeleton } from "@/components/ui/DataTable";
import { Badge, StatusBadge } from "@/components/ui/Badge";
import { formatDateTime } from "@/lib/utils";
import type { UserRole } from "@/types";

const roleVariant: Record<UserRole, "success" | "warning" | "info" | "default"> = {
  platform_admin: "success",
  store_owner: "success",
  store_manager: "info",
  cashier: "warning",
  waiter: "default",
};

export default function PlatformUsersPage() {
  const { data: users, isLoading } = useStaff();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Users</h1>
        <p className="text-sm text-gray-500">All platform users</p>
      </div>

      {isLoading ? (
        <TableSkeleton rows={10} cols={5} />
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
                item.last_login ? formatDateTime(item.last_login) : "—",
            },
          ]}
          data={users?.data ?? []}
          emptyMessage="No users found"
        />
      )}
    </div>
  );
}
