"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import ProductCard from "@/components/ProductCard";
import type { IProduct } from "@/types/product";

export default function ProductListingPage() {
  const [products, setProducts] = useState<IProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchProducts = async () => {
      try {
        const { data } = await api.get("/products/?page_size=100");
        const items = data?.data ?? data?.results ?? [];
        setProducts(items.filter((p: IProduct) => p.is_available));
      } catch (err: any) {
        setError(err.message || "Failed to load products");
      } finally {
        setLoading(false);
      }
    };
    fetchProducts();
  }, []);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-[var(--md-on-surface)]">Shop</h1>
        <p className="mt-1 text-sm text-[var(--md-on-surface-variant)]">
          Browse our products and add items to your cart.
        </p>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div
              key={i}
              className="h-80 animate-pulse rounded-2xl bg-[var(--md-surface-container)]"
            />
          ))}
        </div>
      ) : error ? (
        <div className="py-24 text-center">
          <p className="text-lg text-[var(--md-error)]">{error}</p>
        </div>
      ) : products.length === 0 ? (
        <div className="py-24 text-center">
          <div className="mb-6 text-5xl">🛍️</div>
          <h2 className="text-xl font-semibold text-[var(--md-on-surface)]">
            Products coming soon
          </h2>
          <p className="mt-2 text-[var(--md-on-surface-variant)]">
            Check back shortly — we're setting things up.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {products.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      )}
    </div>
  );
}
