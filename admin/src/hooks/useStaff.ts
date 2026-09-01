import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { IStaff, IApiListResponse } from "@/types";

export function useStaff() {
  return useQuery({
    queryKey: ["staff"],
    queryFn: async () => {
      const { data } = await api.get<IApiListResponse<IStaff>>("/users/");
      return data;
    },
  });
}

export function useCreateStaff() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (staff: Partial<IStaff> & { password: string }) => {
      const { data } = await api.post<{ data: IStaff }>("/users/", staff);
      return data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["staff"] });
    },
  });
}

export function useUpdateStaff() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      ...staff
    }: Partial<IStaff> & { id: string }) => {
      const { data } = await api.patch<{ data: IStaff }>(
        `/users/${id}/`,
        staff
      );
      return data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["staff"] });
    },
  });
}
