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
          "inline-flex items-center justify-center rounded-lg font-medium transition-colors",
          "min-h-[48px] px-4 py-2",
          "disabled:cursor-not-allowed disabled:opacity-50",
          variant === "primary" && "bg-blue-600 text-white hover:bg-blue-700",
          variant === "secondary" && "border border-gray-300 bg-white text-gray-700 hover:bg-gray-50",
          variant === "danger" && "bg-red-600 text-white hover:bg-red-700",
          variant === "ghost" && "text-gray-700 hover:bg-gray-100",
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
