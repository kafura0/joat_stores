import { ButtonHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  size?: "sm" | "md" | "lg";
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", disabled, ...props }, ref) => {
    return (
      <button
        ref={ref}
        disabled={disabled}
        className={cn(
          "inline-flex items-center justify-center rounded-lg font-medium transition-all duration-200",
          "min-h-[48px] px-4 py-2",
          "disabled:cursor-not-allowed disabled:opacity-50",
          variant === "primary" &&
            "bg-gradient-to-r from-[var(--md-primary)] to-[var(--md-primary)] text-white shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-elevated)] hover:opacity-90 active:scale-[0.98]",
          variant === "secondary" &&
            "border border-[var(--md-outline)] bg-[var(--md-surface)] text-[var(--md-on-surface)] hover:bg-[var(--md-surface-variant)]",
          variant === "danger" &&
            "bg-[var(--md-error)] text-white shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-elevated)] hover:opacity-90 active:scale-[0.98]",
          variant === "ghost" &&
            "text-[var(--md-on-surface-variant)] hover:bg-[var(--md-surface-variant)] hover:text-[var(--md-on-surface)]",
          size === "sm" && "min-h-[36px] px-3 text-sm",
          size === "lg" && "min-h-[56px] px-6 text-lg",
          className
        )}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button };
