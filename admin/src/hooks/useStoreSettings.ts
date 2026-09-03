import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface IStoreSettings {
  id: number;
  tagline: string;
  logo_url: string;
  low_stock_threshold: number;
  tax_rate: number;
  tax_inclusive: boolean;
  currency_symbol: string;
  receipt_header: string;
  receipt_footer: string;
}

export function useStoreSettings() {
  return useQuery({
    queryKey: ["store-settings"],
    queryFn: async () => {
      const { data } = await api.get<{ data: IStoreSettings }>("/store/settings/");
      return data.data;
    },
  });
}

export function useUpdateStoreSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (settings: Partial<IStoreSettings>) => {
      const { data } = await api.patch<{ data: IStoreSettings }>(
        "/store/settings/",
        settings
      );
      return data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["store-settings"] });
    },
  });
}
