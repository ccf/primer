import { useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import type {
  CostAnalytics,
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

function buildParams(params: Record<string, string | number | null | undefined>): string {
  const sp = new URLSearchParams()
  for (const [key, val] of Object.entries(params)) {
    if (val != null && val !== "") sp.set(key, String(val))
  }
  const qs = sp.toString()
  return qs ? `?${qs}` : ""
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

export function useOverview(teamId: string | null, startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ["overview", teamId, startDate, endDate],
    queryFn: () =>
      apiFetch<OverviewStats>(
        `/api/v1/analytics/overview${buildParams({ team_id: teamId, start_date: startDate, end_date: endDate })}`,
      ),
  })
}

export function useDailyStats(
  teamId: string | null,
  days = 30,
  startDate?: string,
  endDate?: string,
) {
  return useQuery({
    queryKey: ["daily", teamId, days, startDate, endDate],
    queryFn: () =>
      apiFetch<DailyStatsResponse[]>(
        `/api/v1/analytics/daily${buildParams({ team_id: teamId, days, start_date: startDate, end_date: endDate })}`,
      ),
  })
}

export function useFriction(teamId: string | null, startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ["friction", teamId, startDate, endDate],
    queryFn: () =>
      apiFetch<FrictionReport[]>(
        `/api/v1/analytics/friction${buildParams({ team_id: teamId, start_date: startDate, end_date: endDate })}`,
      ),
  })
}

export function useToolRankings(teamId: string | null, startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ["tools", teamId, startDate, endDate],
    queryFn: () =>
      apiFetch<ToolRanking[]>(
        `/api/v1/analytics/tools${buildParams({ team_id: teamId, start_date: startDate, end_date: endDate })}`,
      ),
  })
}

export function useModelRankings(teamId: string | null, startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ["models", teamId, startDate, endDate],
    queryFn: () =>
      apiFetch<ModelRanking[]>(
        `/api/v1/analytics/models${buildParams({ team_id: teamId, start_date: startDate, end_date: endDate })}`,
      ),
  })
}

export function useRecommendations(teamId: string | null, startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ["recommendations", teamId, startDate, endDate],
    queryFn: () =>
      apiFetch<Recommendation[]>(
        `/api/v1/analytics/recommendations${buildParams({ team_id: teamId, start_date: startDate, end_date: endDate })}`,
      ),
  })
}

export function useCostAnalytics(teamId: string | null, startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ["costs", teamId, startDate, endDate],
    queryFn: () =>
      apiFetch<CostAnalytics>(
        `/api/v1/analytics/costs${buildParams({ team_id: teamId, start_date: startDate, end_date: endDate })}`,
      ),
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
