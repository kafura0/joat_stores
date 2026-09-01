import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { IDashboardStats } from "@/types";

export function useDashboardStats() {
  return useQuery({
    queryKey: ["dashboard"],
    queryFn: async () => {
      const { data } = await api.get<{ data: IDashboardStats }>("/dashboard/");
      return data.data;
    },
    refetchInterval: 30_000,
  });
}
