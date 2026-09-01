import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { IInventoryItem } from "@/types";

export function useInventory(params?: { search?: string; status?: string }) {
  return useQuery({
    queryKey: ["inventory", params],
    queryFn: async () => {
      const { data } = await api.get<{ data: IInventoryItem[] }>(
        "/inventory/",
        { params }
      );
      return data.data;
    },
  });
}
