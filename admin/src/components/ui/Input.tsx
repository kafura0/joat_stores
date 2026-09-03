import { InputHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, id, ...props }, ref) => {
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
        <input
          ref={ref}
          id={id}
          className={cn(
            "block w-full rounded-lg border border-[var(--md-outline)] bg-[var(--md-surface)] px-4 py-3 text-sm text-[var(--md-on-surface)]",
            "placeholder:text-[var(--md-on-surface-variant)]",
            "focus:border-[var(--md-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--md-primary)]",
            "disabled:cursor-not-allowed disabled:bg-[var(--md-surface-variant)] disabled:text-[var(--md-on-surface-variant)]",
            error && "border-[var(--md-error)] focus:border-[var(--md-error)] focus:ring-[var(--md-error)]",
            className
          )}
          style={{ minHeight: 48 }}
          {...props}
        />
        {error && <p className="mt-1 text-sm text-[var(--md-error)]">{error}</p>}
      </div>
    );
  }
);
Input.displayName = "Input";

export { Input };
