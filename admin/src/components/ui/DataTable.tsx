import { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface Column<T> {
  header: string;
  accessor: keyof T | ((item: T) => ReactNode);
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  onRowClick?: (item: T) => void;
  emptyMessage?: string;
  keyAccessor?: (item: T) => string | number;
}

export function DataTable<T>({
  columns,
  data,
  onRowClick,
  emptyMessage = "No data found",
  keyAccessor,
}: DataTableProps<T>) {
  const getKey = keyAccessor ?? ((item: T, index: number) => index);

  if (data.length === 0) {
    return (
      <div className="glass-panel rounded-xl border border-[var(--md-outline-variant)] bg-[var(--md-surface-container)] p-12 text-center backdrop-blur-md">
        <p className="text-[var(--md-on-surface-variant)]">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="glass-panel overflow-hidden rounded-xl border border-[var(--md-outline-variant)] bg-[var(--md-surface-container)] backdrop-blur-md">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="border-b border-[var(--md-outline-variant)] bg-[var(--md-surface-container-high)]">
            <tr>
              {columns.map((col) => (
                <th
                  key={String(col.header)}
                  className={cn(
                    "px-4 py-3 text-left text-sm font-medium text-[var(--md-on-surface-variant)]",
                    col.className
                  )}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((item, index) => (
              <tr
                key={getKey(item, index)}
                onClick={() => onRowClick?.(item)}
                className={cn(
                  "border-b border-[var(--md-outline-variant)] last:border-0 transition-colors",
                  onRowClick && "cursor-pointer hover:bg-[var(--md-surface-variant)]"
                )}
              >
                {columns.map((col) => (
                  <td
                    key={String(col.header)}
                    className={cn(
                      "px-4 py-3 text-sm text-[var(--md-on-surface)]",
                      col.className
                    )}
                  >
                    {typeof col.accessor === "function"
                      ? col.accessor(item)
                      : String(item[col.accessor] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function TableSkeleton({
  rows = 5,
  cols = 4,
}: {
  rows?: number;
  cols?: number;
}) {
  return (
    <div className="glass-panel rounded-xl border border-[var(--md-outline-variant)] bg-[var(--md-surface-container)] p-4 backdrop-blur-md">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4 border-b border-[var(--md-outline-variant)] py-3 last:border-0">
          {Array.from({ length: cols }).map((_, j) => (
            <div
              key={j}
              className="h-4 flex-1 animate-pulse rounded bg-[var(--md-surface-variant)]"
            />
          ))}
        </div>
      ))}
    </div>
  );
}
