import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { IStore, IApiListResponse } from "@/types";

export interface IPlan {
  id: number;
  name: string;
  slug: string;
  price_kes: string;
  monthly_order_limit: number;
  max_staff: number;
  max_products: number;
  has_ai_features: boolean;
  has_api_access: boolean;
  has_white_label: boolean;
  is_active: boolean;
  is_public: boolean;
}

export interface IStoreSubscription {
  id: string;
  store: IStore;
  plan: IPlan;
  status: string;
  renewal_amount_kes: string;
  started_at: string;
  expires_at: string | null;
  created_at: string;
  store__name?: string;
  plan__name?: string;
}

export interface IPlatformMetrics {
  stores: {
    total: number;
    active: number;
    trial: number;
    suspended: number;
    dormant: number;
    by_type: Record<string, number>;
    by_status: Record<string, number>;
    new_mtd: number;
    new_30d: number;
  };
  subscriptions: {
    total: number;
    active: number;
    plan_distribution: Record<string, number>;
    trial_conversion_rate: number;
    expiring_soon: number;
  };
  revenue: {
    mrr: string;
    revenue_mtd: string;
    revenue_30d: string;
    gmv_30d: string;
    failed_renewals: number;
  };
  orders: {
    total: number;
    last_30d: number;
    today: number;
  };
  health: {
    churn_rate: number;
    dormant_stores: number;
  };
  recent_stores: Array<{
    id: string;
    name: string;
    slug: string;
    tenant_type: string;
    status: string;
    created_at: string | null;
  }>;
  recent_subscriptions: Array<{
    id: string;
    status: string;
    renewal_amount_kes: string;
    created_at: string | null;
    store__name: string;
    plan__name: string;
  }>;
}

export function usePlatformMetrics() {
  return useQuery({
    queryKey: ["platform-metrics"],
    queryFn: async () => {
      const { data } = await api.get<IPlatformMetrics>("/platform/metrics/");
      return data;
    },
    refetchInterval: 30000, // auto-refresh every 30s
  });
}

export function usePlatformStores() {
  return useQuery({
    queryKey: ["platform-stores"],
    queryFn: async () => {
      const { data } = await api.get<IApiListResponse<IStore>>(
        "/platform/stores/"
      );
      return data;
    },
  });
}

export interface IOnboarding {
  owner_email: string;
  temporary_password: string;
  storefront_url: string;
}

export function useCreateStore() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (store: {
      name: string;
      domain: string;
      tenant_type: string;
      owner_email: string;
      currency?: string;
      country?: string;
    }) => {
      const { data } = await api.post<{ data: IStore & { onboarding?: IOnboarding } }>(
        "/platform/stores/",
        store
      );
      return data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["platform-stores"] });
      queryClient.invalidateQueries({ queryKey: ["platform-metrics"] });
    },
  });
}

export function useUpdateStoreStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) => {
      const { data } = await api.patch<{ data: IStore }>(
        `/platform/stores/${id}/status/`,
        { status }
      );
      return data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["platform-stores"] });
      queryClient.invalidateQueries({ queryKey: ["platform-metrics"] });
    },
  });
}

export function usePlans() {
  return useQuery({
    queryKey: ["plans"],
    queryFn: async () => {
      const { data } = await api.get<IPlan[]>("/saas/plans/");
      return data;
    },
  });
}

export function useCreatePlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (plan: Partial<IPlan>) => {
      const { data } = await api.post<IPlan>("/saas/plans/", plan);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["plans"] });
    },
  });
}

export function usePlatformSubscriptions() {
  return useQuery({
    queryKey: ["platform-subscriptions"],
    queryFn: async () => {
      const { data } = await api.get<IStoreSubscription[]>(
        "/platform/subscriptions/"
      );
      return data;
    },
  });
}

export function useUpdateSubscription() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      ...payload
    }: { id: string; status?: string; plan_id?: number }) => {
      const { data } = await api.patch<IStoreSubscription>(
        `/platform/subscriptions/${id}/`,
        payload
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["platform-subscriptions"],
      });
      queryClient.invalidateQueries({ queryKey: ["platform-stores"] });
      queryClient.invalidateQueries({ queryKey: ["platform-metrics"] });
    },
  });
}
