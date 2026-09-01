import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ICartItem } from "@/types";

export function useCart() {
  return useQuery({
    queryKey: ["cart"],
    queryFn: async () => {
      const { data } = await api.get<{ data: ICartItem[] }>("/cart/");
      return data.data;
    },
  });
}

export function useAddToCart() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (item: { variant_id: number; quantity: number }) => {
      const { data } = await api.post<{ data: ICartItem }>("/cart/", item);
      return data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cart"] });
    },
  });
}

export function useUpdateCartItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      itemId,
      quantity,
    }: {
      itemId: number;
      quantity: number;
    }) => {
      const { data } = await api.patch<{ data: ICartItem }>(
        `/cart/${itemId}/`,
        { quantity }
      );
      return data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cart"] });
    },
  });
}

export function useRemoveCartItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (itemId: number) => {
      await api.delete(`/cart/${itemId}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cart"] });
    },
  });
}

export function useCheckout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      payment_method: "cash" | "mpesa" | "card";
      customer_id?: number;
      notes?: string;
    }) => {
      const { data } = await api.post<{ data: { order_id: string } }>(
        "/checkout/",
        payload
      );
      return data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cart"] });
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
