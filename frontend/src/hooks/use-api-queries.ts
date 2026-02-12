import { useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import type {
  DailyStatsResponse,
  EngineerResponse,
  FrictionReport,
  ModelRanking,
  OverviewStats,
  Recommendation,
  SessionDetailResponse,
  SessionResponse,
  TeamResponse,
  ToolRanking,
} from "@/types/api"

function teamParam(teamId: string | null) {
  return teamId ? `?team_id=${teamId}` : ""
}

export function useTeams() {
  return useQuery({
    queryKey: ["teams"],
    queryFn: () => apiFetch<TeamResponse[]>("/api/v1/teams"),
  })
}

export function useEngineers() {
  return useQuery({
    queryKey: ["engineers"],
    queryFn: () => apiFetch<EngineerResponse[]>("/api/v1/engineers"),
  })
}

export function useOverview(teamId: string | null) {
  return useQuery({
    queryKey: ["overview", teamId],
    queryFn: () => apiFetch<OverviewStats>(`/api/v1/analytics/overview${teamParam(teamId)}`),
  })
}

export function useDailyStats(teamId: string | null, days = 30) {
  return useQuery({
    queryKey: ["daily", teamId, days],
    queryFn: () =>
      apiFetch<DailyStatsResponse[]>(
        `/api/v1/analytics/daily${teamParam(teamId)}${teamId ? "&" : "?"}days=${days}`,
      ),
  })
}

export function useFriction(teamId: string | null) {
  return useQuery({
    queryKey: ["friction", teamId],
    queryFn: () => apiFetch<FrictionReport[]>(`/api/v1/analytics/friction${teamParam(teamId)}`),
  })
}

export function useToolRankings(teamId: string | null) {
  return useQuery({
    queryKey: ["tools", teamId],
    queryFn: () => apiFetch<ToolRanking[]>(`/api/v1/analytics/tools${teamParam(teamId)}`),
  })
}

export function useModelRankings(teamId: string | null) {
  return useQuery({
    queryKey: ["models", teamId],
    queryFn: () => apiFetch<ModelRanking[]>(`/api/v1/analytics/models${teamParam(teamId)}`),
  })
}

export function useRecommendations(teamId: string | null) {
  return useQuery({
    queryKey: ["recommendations", teamId],
    queryFn: () =>
      apiFetch<Recommendation[]>(`/api/v1/analytics/recommendations${teamParam(teamId)}`),
  })
}

export function useSessions(params: {
  teamId: string | null
  engineerId?: string
  limit?: number
  offset?: number
}) {
  const searchParams = new URLSearchParams()
  if (params.teamId) searchParams.set("team_id", params.teamId)
  if (params.engineerId) searchParams.set("engineer_id", params.engineerId)
  if (params.limit) searchParams.set("limit", String(params.limit))
  if (params.offset) searchParams.set("offset", String(params.offset))
  const qs = searchParams.toString()
  return useQuery({
    queryKey: ["sessions", params],
    queryFn: () => apiFetch<SessionResponse[]>(`/api/v1/sessions${qs ? `?${qs}` : ""}`),
  })
}

export function useSessionDetail(sessionId: string) {
  return useQuery({
    queryKey: ["session", sessionId],
    queryFn: () => apiFetch<SessionDetailResponse>(`/api/v1/sessions/${sessionId}`),
    enabled: !!sessionId,
  })
}
