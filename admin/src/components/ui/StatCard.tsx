import { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string | number;
  change?: string;
  icon?: ReactNode;
}

export function StatCard({ label, value, change, icon }: StatCardProps) {
  return (
    <div className="rounded-lg border bg-white p-6">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-gray-500">{label}</p>
        {icon && <div className="text-gray-400">{icon}</div>}
      </div>
      <p className="mt-2 text-2xl font-semibold text-gray-900">{value}</p>
      {change && (
        <p
          className={cn(
            "mt-1 text-xs",
            change.startsWith("+") ? "text-green-600" : "text-red-600"
          )}
        >
          {change}
        </p>
      )}
    </div>
  );
}

export function StatCardSkeleton() {
  return (
    <div className="rounded-lg border bg-white p-6">
      <div className="h-4 w-24 animate-pulse rounded bg-gray-200" />
      <div className="mt-2 h-8 w-32 animate-pulse rounded bg-gray-200" />
      <div className="mt-1 h-3 w-20 animate-pulse rounded bg-gray-200" />
    </div>
  );
}
