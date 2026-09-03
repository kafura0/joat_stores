import { cn } from "@/lib/utils";

export function LoadingSpinner({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center justify-center", className)}>
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-[var(--md-outline)] border-t-[var(--md-primary)]" />
    </div>
  );
}

export function PageLoading() {
  return (
    <div className="flex min-h-[400px] items-center justify-center">
      <LoadingSpinner />
    </div>
  );
}

export function InlineLoading() {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-[var(--md-on-surface-variant)]">
      <div className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--md-outline)] border-t-[var(--md-primary)]" />
      Loading...
    </span>
  );
}
