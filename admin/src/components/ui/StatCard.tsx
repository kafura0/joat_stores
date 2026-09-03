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
    <div className="premium-card rounded-xl border border-[var(--md-outline-variant)] bg-[var(--md-surface-container)] p-6 backdrop-blur-md transition-all duration-200 hover:shadow-[var(--shadow-elevated)] hover:-translate-y-0.5">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-[var(--md-on-surface-variant)]">{label}</p>
        {icon && <div className="text-[var(--md-tertiary)]">{icon}</div>}
      </div>
      <p className="mt-2 text-2xl font-semibold text-[var(--md-on-surface)]">{value}</p>
      {change && (
        <p
          className={cn(
            "mt-1 text-xs",
            change.startsWith("+") || change.includes("need") === false
              ? "text-[var(--md-success)]"
              : "text-[var(--md-warning)]"
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
    <div className="rounded-xl border border-[var(--md-outline-variant)] bg-[var(--md-surface-container)] p-6">
      <div className="h-4 w-24 animate-pulse rounded bg-[var(--md-surface-variant)]" />
      <div className="mt-2 h-8 w-32 animate-pulse rounded bg-[var(--md-surface-variant)]" />
      <div className="mt-1 h-3 w-20 animate-pulse rounded bg-[var(--md-surface-variant)]" />
    </div>
  );
}
