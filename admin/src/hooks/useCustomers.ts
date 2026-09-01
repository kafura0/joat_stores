import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ICustomer, IApiListResponse } from "@/types";

export function useCustomers(params?: { search?: string }) {
  return useQuery({
    queryKey: ["customers", params],
    queryFn: async () => {
      const { data } = await api.get<IApiListResponse<ICustomer>>(
        "/customers/",
        { params }
      );
      return data;
    },
  });
}

export function useCustomer(id: number) {
  return useQuery({
    queryKey: ["customer", id],
    queryFn: async () => {
      const { data } = await api.get<{ data: ICustomer }>(
        `/customers/${id}/`
      );
      return data.data;
    },
    enabled: !!id,
  });
}

export function useCreateCustomer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (customer: Partial<ICustomer>) => {
      const { data } = await api.post<{ data: ICustomer }>(
        "/customers/",
        customer
      );
      return data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["customers"] });
    },
  });
}
