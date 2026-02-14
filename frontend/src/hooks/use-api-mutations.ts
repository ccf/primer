import { useMutation, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"

export function useAcknowledgeAlert() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (alertId: string) =>
      apiFetch(`/api/v1/alerts/${alertId}/acknowledge`, { method: "PATCH" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  })
}

export function useDismissAlert() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (alertId: string) =>
      apiFetch(`/api/v1/alerts/${alertId}/dismiss`, { method: "PATCH" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  })
}

export function useDeactivateEngineer() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (engineerId: string) =>
      apiFetch(`/api/v1/engineers/${engineerId}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["engineers"] }),
  })
}

export function useRotateApiKey() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (engineerId: string) =>
      apiFetch<{ api_key: string; engineer: unknown }>(
        `/api/v1/engineers/${engineerId}/rotate-key`,
        { method: "POST" },
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["engineers"] }),
  })
}

export function useUpdateEngineerRole() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ engineerId, role }: { engineerId: string; role: string }) =>
      apiFetch(`/api/v1/engineers/${engineerId}`, {
        method: "PATCH",
        body: JSON.stringify({ role }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["engineers"] }),
  })
}

export function useCreateTeam() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (name: string) =>
      apiFetch("/api/v1/teams", {
        method: "POST",
        body: JSON.stringify({ name }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["teams"] }),
  })
}

export function useCreateEngineer() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { name: string; email: string; team_id?: string }) =>
      apiFetch<{ api_key: string; engineer: unknown }>("/api/v1/engineers", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["engineers"] }),
  })
}
