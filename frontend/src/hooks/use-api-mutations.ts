import { useMutation, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import type { AlertConfigResponse, NarrativeResponse } from "@/types/api"

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

export function useTestSlack() {
  return useMutation({
    mutationFn: () =>
      apiFetch<{ success: boolean; error?: string }>("/api/v1/notifications/slack/test", {
        method: "POST",
      }),
  })
}

export function useCreateAlertConfig() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: { team_id?: string | null; alert_type: string; enabled?: boolean; threshold: number }) =>
      apiFetch<AlertConfigResponse>("/api/v1/alert-configs", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alert-configs"] })
      qc.invalidateQueries({ queryKey: ["alert-thresholds"] })
    },
  })
}

export function useUpdateAlertConfig() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...payload }: { id: string; enabled?: boolean; threshold?: number }) =>
      apiFetch<AlertConfigResponse>(`/api/v1/alert-configs/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alert-configs"] })
      qc.invalidateQueries({ queryKey: ["alert-thresholds"] })
    },
  })
}

export function useDeleteAlertConfig() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<void>(`/api/v1/alert-configs/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alert-configs"] })
      qc.invalidateQueries({ queryKey: ["alert-thresholds"] })
    },
  })
}

export function useRefreshNarrative() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (params: {
      scope: string
      teamId?: string | null
      startDate?: string
      endDate?: string
      engineerId?: string | null
    }) => {
      const sp = new URLSearchParams()
      sp.set("scope", params.scope)
      sp.set("force_refresh", "true")
      if (params.teamId) sp.set("team_id", params.teamId)
      if (params.engineerId) sp.set("engineer_id", params.engineerId)
      if (params.startDate) sp.set("start_date", params.startDate)
      if (params.endDate) sp.set("end_date", params.endDate)
      return apiFetch<NarrativeResponse>(`/api/v1/analytics/narrative?${sp.toString()}`)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["narrative"] }),
  })
}
