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
      className="flex flex-col items-center rounded-lg border bg-white p-4 transition hover:border-blue-500 hover:shadow-md active:scale-95"
      style={{ minHeight: 48 }}
    >
      {image ? (
        <img
          src={image}
          alt={name}
          className="mb-2 h-16 w-16 rounded object-cover"
        />
      ) : (
        <div className="mb-2 flex h-16 w-16 items-center justify-center rounded bg-gray-100 text-2xl font-bold text-gray-400">
          {name[0]}
        </div>
      )}
      <span className="w-full truncate text-center text-sm font-medium">
        {name}
      </span>
      <span className="text-sm font-semibold text-blue-600">
        {formatCurrency(price)}
      </span>
    </button>
  );
}
