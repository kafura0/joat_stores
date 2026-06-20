/**
 * Data fetching hook for admin dashboard pages.
 *
 * Provides a standardized pattern for API calls with loading, error, and data
 * states. Uses the same Axios instance (api) as the rest of the admin so auth
 * interceptors work automatically.
 *
 * Usage:
 *   const { data, isLoading, error } = useApi<IOrder[]>("/store/orders/");
 *
 * Implementation: Story 4.3 (admin data layer)
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/lib/api";

interface UseApiState<T> {
  data: T | null;
  isLoading: boolean;
  error: string | null;
}

interface UseApiReturn<T> extends UseApiState<T> {
  refresh: () => void;
}

export function useApi<T = unknown>(
  url: string,
  options?: { enabled?: boolean },
): UseApiReturn<T> {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    isLoading: true,
    error: null,
  });
  const mountedRef = useRef(true);
  const enabled = options?.enabled ?? true;

  const fetchData = useCallback(async () => {
    if (!url || !enabled) return;

    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const res = await api.get<{ data: T }>(url);
      if (mountedRef.current) {
        setState({ data: res.data.data ?? (res.data as unknown as T), isLoading: false, error: null });
      }
    } catch (err: unknown) {
      if (mountedRef.current) {
        const message =
          err instanceof Error ? err.message : "An unexpected error occurred.";
        setState({ data: null, isLoading: false, error: message });
      }
    }
  }, [url, enabled]);

  useEffect(() => {
    mountedRef.current = true;
    fetchData();
    return () => {
      mountedRef.current = false;
    };
  }, [fetchData]);

  return { ...state, refresh: fetchData };
}
