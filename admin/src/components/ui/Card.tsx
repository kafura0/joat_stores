import { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface CardProps {
  children: ReactNode;
  className?: string;
}

function Card({ children, className }: CardProps) {
  return (
    <div
      className={cn(
        "glass-panel rounded-xl border border-[var(--md-outline-variant)] bg-[var(--md-surface-container)] backdrop-blur-md",
        className
      )}
    >
      {children}
    </div>
  );
}

function CardHeader({ children, className }: CardProps) {
  return (
    <div
      className={cn(
        "border-b border-[var(--md-outline-variant)] px-6 py-4",
        className
      )}
    >
      {children}
    </div>
  );
}

function CardContent({ children, className }: CardProps) {
  return <div className={cn("px-6 py-4", className)}>{children}</div>;
}

export { Card, CardHeader, CardContent };
