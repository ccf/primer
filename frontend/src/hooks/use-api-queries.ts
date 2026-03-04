import { useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import type {
  ActivityHeatmap,
  AlertConfigResponse,
  AlertResponse,
  AlertThresholds,
  AuditLogResponse,
  BottleneckAnalytics,
  BudgetStatus,
  CacheAnalyticsResponse,
  ClaudePRComparisonResponse,
  ConfigOptimizationResponse,
  CostAnalytics,
  CostForecastResponse,
  CostModelingResponse,
  DailyStatsResponse,
  EngineerAnalytics,
  EngineerBenchmarkResponse,
  EngineerProfileResponse,
  EngineerResponse,
  FrictionReport,
  IngestEventResponse,
  LearningPathsResponse,
  MaturityAnalyticsResponse,
  ModelRanking,
  NarrativeResponse,
  NarrativeStatusResponse,
  OnboardingAccelerationResponse,
  OverviewStats,
  PaginatedResponse,
  PatternSharingResponse,
  PersonalizedTipsResponse,
  ProductivityMetrics,
  ProjectAnalytics,
  QualityMetricsResponse,
  Recommendation,
  SessionDetailResponse,
  SessionMessage,
  SessionResponse,
  SimilarSessionsResponse,
  SkillInventoryResponse,
  SystemStats,
  TeamResponse,
  TimeToTeamAverageResponse,
  ToolAdoptionAnalytics,
  SessionInsightsResponse,
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

export function useTeam(teamId: string) {
  return useQuery({
    queryKey: ["team", teamId],
    queryFn: () => apiFetch<TeamResponse>(`/api/v1/teams/${teamId}`),
    enabled: !!teamId,
  })
}

export function useEngineers(includeInactive = false) {
  return useQuery({
    queryKey: ["engineers", includeInactive],
    queryFn: () =>
      apiFetch<EngineerResponse[]>(
        `/api/v1/engineers${includeInactive ? "?include_inactive=true" : ""}`,
      ),
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
  projectName?: string
  search?: string
  outcome?: string
  sessionType?: string
  primaryModel?: string
  gitBranch?: string
  startDate?: string
  endDate?: string
  limit?: number
  offset?: number
}) {
  const qs = buildParams({
    team_id: params.teamId,
    engineer_id: params.engineerId,
    project_name: params.projectName,
    search: params.search,
    outcome: params.outcome,
    session_type: params.sessionType,
    primary_model: params.primaryModel,
    git_branch: params.gitBranch,
    start_date: params.startDate,
    end_date: params.endDate,
    limit: params.limit,
    offset: params.offset,
  })
  return useQuery({
    queryKey: ["sessions", params],
    queryFn: () => apiFetch<PaginatedResponse<SessionResponse>>(`/api/v1/sessions${qs}`),
  })
}

export function useEngineerAnalytics(
  teamId: string | null,
  startDate?: string,
  endDate?: string,
  sortBy?: string,
) {
  return useQuery({
    queryKey: ["engineer-analytics", teamId, startDate, endDate, sortBy],
    queryFn: () =>
      apiFetch<EngineerAnalytics>(
        `/api/v1/analytics/engineers${buildParams({ team_id: teamId, start_date: startDate, end_date: endDate, sort_by: sortBy })}`,
      ),
  })
}

export function useProjectAnalytics(
  teamId: string | null,
  startDate?: string,
  endDate?: string,
  sortBy?: string,
) {
  return useQuery({
    queryKey: ["project-analytics", teamId, startDate, endDate, sortBy],
    queryFn: () =>
      apiFetch<ProjectAnalytics>(
        `/api/v1/analytics/projects${buildParams({ team_id: teamId, start_date: startDate, end_date: endDate, sort_by: sortBy })}`,
      ),
  })
}

export function useActivityHeatmap(teamId: string | null, startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ["activity-heatmap", teamId, startDate, endDate],
    queryFn: () =>
      apiFetch<ActivityHeatmap>(
        `/api/v1/analytics/activity-heatmap${buildParams({ team_id: teamId, start_date: startDate, end_date: endDate })}`,
      ),
  })
}

export function useSessionDetail(sessionId: string) {
  return useQuery({
    queryKey: ["session", sessionId],
    queryFn: () => apiFetch<SessionDetailResponse>(`/api/v1/sessions/${sessionId}`),
    enabled: !!sessionId,
  })
}

export function useTranscript(sessionId: string) {
  return useQuery({
    queryKey: ["transcript", sessionId],
    queryFn: () => apiFetch<SessionMessage[]>(`/api/v1/sessions/${sessionId}/transcript`),
    enabled: !!sessionId,
  })
}

export function useProductivity(teamId: string | null, startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ["productivity", teamId, startDate, endDate],
    queryFn: () =>
      apiFetch<ProductivityMetrics>(
        `/api/v1/analytics/productivity${buildParams({ team_id: teamId, start_date: startDate, end_date: endDate })}`,
      ),
  })
}

export function useEngineerBenchmarks(
  teamId: string | null,
  startDate?: string,
  endDate?: string,
  enabled = true,
) {
  return useQuery({
    queryKey: ["benchmarks", teamId, startDate, endDate],
    queryFn: () =>
      apiFetch<EngineerBenchmarkResponse>(
        `/api/v1/analytics/engineers/benchmarks${buildParams({ team_id: teamId, start_date: startDate, end_date: endDate })}`,
      ),
    enabled,
  })
}

export function useAlerts(acknowledged?: boolean) {
  return useQuery({
    queryKey: ["alerts", acknowledged],
    queryFn: () => {
      const params = new URLSearchParams()
      if (acknowledged !== undefined) params.set("acknowledged", String(acknowledged))
      const qs = params.toString()
      return apiFetch<AlertResponse[]>(`/api/v1/alerts${qs ? `?${qs}` : ""}`)
    },
    refetchInterval: 60_000,
  })
}

export function useSystemStats() {
  return useQuery({
    queryKey: ["system-stats"],
    queryFn: () => apiFetch<SystemStats>("/api/v1/admin/system-stats"),
  })
}

export function useIngestEvents(params?: { engineerId?: string; status?: string; limit?: number; offset?: number }) {
  return useQuery({
    queryKey: ["ingest-events", params],
    queryFn: () => {
      const sp = new URLSearchParams()
      if (params?.engineerId) sp.set("engineer_id", params.engineerId)
      if (params?.status) sp.set("status", params.status)
      if (params?.limit != null) sp.set("limit", String(params.limit))
      if (params?.offset != null) sp.set("offset", String(params.offset))
      const qs = sp.toString()
      return apiFetch<PaginatedResponse<IngestEventResponse>>(`/api/v1/admin/ingest-events${qs ? `?${qs}` : ""}`)
    },
  })
}

export function useAlertConfigs(teamId?: string | null) {
  return useQuery({
    queryKey: ["alert-configs", teamId],
    queryFn: () =>
      apiFetch<AlertConfigResponse[]>(
        `/api/v1/alert-configs${buildParams({ team_id: teamId })}`,
      ),
  })
}

export function useResolvedThresholds(teamId?: string | null) {
  return useQuery({
    queryKey: ["alert-thresholds", teamId],
    queryFn: () =>
      apiFetch<AlertThresholds>(
        `/api/v1/alert-configs/resolved${buildParams({ team_id: teamId })}`,
      ),
  })
}

export function useBottleneckAnalytics(
  teamId: string | null,
  startDate?: string,
  endDate?: string,
) {
  return useQuery({
    queryKey: ["bottlenecks", teamId, startDate, endDate],
    queryFn: () =>
      apiFetch<BottleneckAnalytics>(
        `/api/v1/analytics/bottlenecks${buildParams({ team_id: teamId, start_date: startDate, end_date: endDate })}`,
      ),
  })
}

export function useToolAdoption(teamId: string | null, startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ["tool-adoption", teamId, startDate, endDate],
    queryFn: () =>
      apiFetch<ToolAdoptionAnalytics>(
        `/api/v1/analytics/tool-adoption${buildParams({ team_id: teamId, start_date: startDate, end_date: endDate })}`,
      ),
  })
}

export function useSlackConfig() {
  return useQuery({
    queryKey: ["slack-config"],
    queryFn: () => apiFetch<{ webhook_url_set: boolean; enabled: boolean }>("/api/v1/notifications/slack"),
  })
}

export function useAuditLogs(params?: {
  resource_type?: string
  action?: string
  actor_id?: string
  limit?: number
  offset?: number
}) {
  return useQuery({
    queryKey: ["audit-logs", params],
    queryFn: () =>
      apiFetch<PaginatedResponse<AuditLogResponse>>(
        `/api/v1/admin/audit-logs${buildParams(params ?? {})}`,
      ),
  })
}

export function useConfigOptimization(teamId: string | null, startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ["config-optimization", teamId, startDate, endDate],
    queryFn: () =>
      apiFetch<ConfigOptimizationResponse>(
        `/api/v1/analytics/config-optimization${buildParams({ team_id: teamId, start_date: startDate, end_date: endDate })}`,
      ),
  })
}

export function usePersonalizedTips(teamId: string | null, startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ["personalized-tips", teamId, startDate, endDate],
    queryFn: () =>
      apiFetch<PersonalizedTipsResponse>(
        `/api/v1/analytics/personalized-tips${buildParams({ team_id: teamId, start_date: startDate, end_date: endDate })}`,
      ),
  })
}

export function useSkillInventory(teamId: string | null, startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ["skill-inventory", teamId, startDate, endDate],
    queryFn: () =>
      apiFetch<SkillInventoryResponse>(
        `/api/v1/analytics/skill-inventory${buildParams({ team_id: teamId, start_date: startDate, end_date: endDate })}`,
      ),
  })
}

export function useLearningPaths(teamId: string | null, startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ["learning-paths", teamId, startDate, endDate],
    queryFn: () =>
      apiFetch<LearningPathsResponse>(
        `/api/v1/analytics/learning-paths${buildParams({ team_id: teamId, start_date: startDate, end_date: endDate })}`,
      ),
  })
}

export function usePatternSharing(teamId: string | null, startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ["pattern-sharing", teamId, startDate, endDate],
    queryFn: () =>
      apiFetch<PatternSharingResponse>(
        `/api/v1/analytics/pattern-sharing${buildParams({ team_id: teamId, start_date: startDate, end_date: endDate })}`,
      ),
  })
}

export function useOnboardingAcceleration(teamId: string | null, startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ["onboarding-acceleration", teamId, startDate, endDate],
    queryFn: () =>
      apiFetch<OnboardingAccelerationResponse>(
        `/api/v1/analytics/onboarding-acceleration${buildParams({ team_id: teamId, start_date: startDate, end_date: endDate })}`,
      ),
  })
}

export function useQualityMetrics(teamId: string | null, startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ["quality-metrics", teamId, startDate, endDate],
    queryFn: () =>
      apiFetch<QualityMetricsResponse>(
        `/api/v1/analytics/quality-metrics${buildParams({ team_id: teamId, start_date: startDate, end_date: endDate })}`,
      ),
  })
}

export function useSessionInsights(teamId: string | null, startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ["session-insights", teamId, startDate, endDate],
    queryFn: () =>
      apiFetch<SessionInsightsResponse>(
        `/api/v1/analytics/session-insights${buildParams({ team_id: teamId, start_date: startDate, end_date: endDate })}`,
      ),
  })
}

export function useEngineerProfile(engineerId: string, startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ["engineer-profile", engineerId, startDate, endDate],
    queryFn: () =>
      apiFetch<EngineerProfileResponse>(
        `/api/v1/analytics/engineers/${engineerId}/profile${buildParams({ start_date: startDate, end_date: endDate })}`,
      ),
    enabled: !!engineerId,
  })
}

export function useSimilarSessions(sessionId: string) {
  return useQuery({
    queryKey: ["similar-sessions", sessionId],
    queryFn: () =>
      apiFetch<SimilarSessionsResponse>(`/api/v1/sessions/${sessionId}/similar`),
    enabled: !!sessionId,
  })
}

export function useClaudePRComparison(teamId: string | null, startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ["claude-pr-comparison", teamId, startDate, endDate],
    queryFn: () =>
      apiFetch<ClaudePRComparisonResponse>(
        `/api/v1/analytics/claude-pr-comparison${buildParams({ team_id: teamId, start_date: startDate, end_date: endDate })}`,
      ),
  })
}

export function useTimeToTeamAverage(teamId: string | null, startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ["time-to-team-average", teamId, startDate, endDate],
    queryFn: () =>
      apiFetch<TimeToTeamAverageResponse>(
        `/api/v1/analytics/time-to-team-average${buildParams({ team_id: teamId, start_date: startDate, end_date: endDate })}`,
      ),
  })
}

export function useMaturityAnalytics(teamId: string | null, startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ["maturity-analytics", teamId, startDate, endDate],
    queryFn: () =>
      apiFetch<MaturityAnalyticsResponse>(
        `/api/v1/analytics/maturity${buildParams({ team_id: teamId, start_date: startDate, end_date: endDate })}`,
      ),
  })
}

export function useNarrativeStatus() {
  return useQuery({
    queryKey: ["narrative-status"],
    queryFn: () => apiFetch<NarrativeStatusResponse>("/api/v1/analytics/narrative/status"),
    staleTime: 5 * 60 * 1000,
  })
}

export function useNarrative(
  scope: string,
  teamId?: string | null,
  startDate?: string,
  endDate?: string,
  enabled = true,
  engineerId?: string | null,
) {
  return useQuery({
    queryKey: ["narrative", scope, teamId, startDate, endDate, engineerId],
    queryFn: () =>
      apiFetch<NarrativeResponse>(
        `/api/v1/analytics/narrative${buildParams({ scope, team_id: teamId, engineer_id: engineerId, start_date: startDate, end_date: endDate })}`,
      ),
    enabled,
    staleTime: 5 * 60 * 1000,
    retry: 0,
  })
}

// --- FinOps ---

export function useCacheAnalytics(teamId: string | null, startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ["finops-cache", teamId, startDate, endDate],
    queryFn: () =>
      apiFetch<CacheAnalyticsResponse>(
        `/api/v1/finops/cache${buildParams({ team_id: teamId, start_date: startDate, end_date: endDate })}`,
      ),
  })
}

export function useCostModeling(
  teamId: string | null,
  startDate?: string,
  endDate?: string,
) {
  return useQuery({
    queryKey: ["finops-cost-modeling", teamId, startDate, endDate],
    queryFn: () =>
      apiFetch<CostModelingResponse>(
        `/api/v1/finops/cost-modeling${buildParams({ team_id: teamId, start_date: startDate, end_date: endDate })}`,
      ),
  })
}

export function useCostForecast(
  teamId: string | null,
  startDate?: string,
  endDate?: string,
  forecastDays = 30,
) {
  return useQuery({
    queryKey: ["finops-forecast", teamId, startDate, endDate, forecastDays],
    queryFn: () =>
      apiFetch<CostForecastResponse>(
        `/api/v1/finops/forecast${buildParams({ team_id: teamId, start_date: startDate, end_date: endDate, forecast_days: forecastDays })}`,
      ),
  })
}

export function useBudgets(teamId: string | null) {
  return useQuery({
    queryKey: ["finops-budgets", teamId],
    queryFn: () =>
      apiFetch<BudgetStatus[]>(
        `/api/v1/finops/budgets${buildParams({ team_id: teamId })}`,
      ),
  })
}
