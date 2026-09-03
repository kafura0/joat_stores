import { SelectHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  options: { value: string | number; label: string }[];
}

const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, error, id, options, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={id}
            className="mb-1 block text-sm font-medium text-[var(--md-on-surface-variant)]"
          >
            {label}
          </label>
        )}
        <select
          ref={ref}
          id={id}
          className={cn(
            "block w-full rounded-lg border border-[var(--md-outline)] bg-[var(--md-surface)] px-4 py-3 text-sm text-[var(--md-on-surface)]",
            "focus:border-[var(--md-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--md-primary)]",
            "disabled:cursor-not-allowed disabled:bg-[var(--md-surface-variant)] disabled:text-[var(--md-on-surface-variant)]",
            error && "border-[var(--md-error)] focus:border-[var(--md-error)] focus:ring-[var(--md-error)]",
            className
          )}
          style={{ minHeight: 48 }}
          {...props}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {error && <p className="mt-1 text-sm text-[var(--md-error)]">{error}</p>}
      </div>
    );
  }
);
Select.displayName = "Select";

export { Select };
