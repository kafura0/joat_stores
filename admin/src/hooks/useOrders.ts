import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { IOrder, IApiListResponse } from "@/types";

export function useOrders(params?: {
  status?: string;
  payment_method?: string;
}) {
  return useQuery({
    queryKey: ["orders", params],
    queryFn: async () => {
      const { data } = await api.get<IApiListResponse<IOrder>>("/orders/", {
        params,
      });
      return data;
    },
  });
}

export function useOrder(id: string) {
  return useQuery({
    queryKey: ["order", id],
    queryFn: async () => {
      const { data } = await api.get<{ data: IOrder }>(`/orders/${id}/`);
      return data.data;
    },
    enabled: !!id,
  });
}
