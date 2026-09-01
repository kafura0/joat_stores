import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { IStore, IApiListResponse } from "@/types";

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
