"use client";

import { formatCurrency } from "@/lib/utils";

interface ProductCardProps {
  name: string;
  price: string;
  image?: string;
  onAdd: () => void;
}

export function ProductCard({ name, price, image, onAdd }: ProductCardProps) {
  return (
    <button
      onClick={onAdd}
      className="glass-panel flex flex-col items-center rounded-xl border border-[var(--md-outline-variant)] bg-[var(--glass-bg)] p-4 backdrop-blur-md transition-all duration-200 hover:border-[var(--md-primary)] hover:shadow-[var(--shadow-elevated)] hover:scale-[1.02] active:scale-95"
      style={{ minHeight: 48 }}
    >
      {image ? (
        <img
          src={image}
          alt={name}
          className="mb-2 h-16 w-16 rounded-lg object-cover"
        />
      ) : (
        <div className="mb-2 flex h-16 w-16 items-center justify-center rounded-lg bg-[var(--md-primary-container)] text-2xl font-bold text-[var(--md-on-primary-container)]">
          {name[0]}
        </div>
      )}
      <span className="w-full truncate text-center text-sm font-medium text-[var(--md-on-surface)]">
        {name}
      </span>
      <span className="text-sm font-semibold text-[var(--md-primary)]">
        {formatCurrency(price)}
      </span>
    </button>
  );
}
