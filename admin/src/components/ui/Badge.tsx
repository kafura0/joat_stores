import { cn } from "@/lib/utils";

type BadgeVariant = "success" | "warning" | "danger" | "info" | "default";

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  success: "bg-[var(--md-success-container)] text-[var(--md-success)]",
  warning: "bg-[var(--md-warning-container)] text-[var(--md-warning)]",
  danger: "bg-[var(--md-error-container)] text-[var(--md-error)]",
  info: "bg-[var(--md-tertiary-container)] text-[var(--md-tertiary)]",
  default: "bg-[var(--md-secondary-container)] text-[var(--md-on-secondary-container)]",
};

export function Badge({ children, variant = "default", className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        variantStyles[variant],
        className
      )}
    >
      {children}
    </span>
  );
}

export function StatusBadge({ active }: { active: boolean }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className={cn(
          "h-2 w-2 rounded-full",
          active ? "bg-[var(--md-success)]" : "bg-[var(--md-outline)]"
        )}
      />
      <span className="text-sm text-[var(--md-on-surface-variant)]">{active ? "Active" : "Inactive"}</span>
    </span>
  );
}
