export interface TeamResponse {
  id: string
  name: string
  created_at: string
  engineer_count?: number
}

export interface EngineerResponse {
  id: string
  name: string
  email: string
  team_id: string | null
  role: string
  avatar_url: string | null
  github_username: string | null
  display_name: string | null
  is_active: boolean
  created_at: string
}

export interface SessionResponse {
  id: string
  engineer_id: string
  project_path: string | null
  project_name: string | null
  git_branch: string | null
  claude_version: string | null
  permission_mode: string | null
  end_reason: string | null
  started_at: string | null
  ended_at: string | null
  duration_seconds: number | null
  message_count: number
  user_message_count: number
  assistant_message_count: number
  tool_call_count: number
  input_tokens: number
  output_tokens: number
  cache_read_tokens: number
  cache_creation_tokens: number
  primary_model: string | null
  first_prompt: string | null
  summary: string | null
  has_facets: boolean
  created_at: string
}

export interface SessionFacetsResponse {
  underlying_goal: string | null
  goal_categories: string[] | null
  outcome: string | null
  session_type: string | null
  primary_success: string | null
  claude_helpfulness: string | null
  brief_summary: string | null
  user_satisfaction_counts: Record<string, number> | null
  friction_counts: Record<string, number> | null
  friction_detail: string | null
  created_at: string
}

export interface ToolUsageResponse {
  tool_name: string
  call_count: number
}

export interface ModelUsageResponse {
  model_name: string
  input_tokens: number
  output_tokens: number
  cache_read_tokens: number
  cache_creation_tokens: number
}

export interface SessionDetailResponse extends SessionResponse {
  facets: SessionFacetsResponse | null
  tool_usages: ToolUsageResponse[]
  model_usages: ModelUsageResponse[]
}

export interface OverviewStats {
  total_sessions: number
  total_engineers: number
  total_messages: number
  total_tool_calls: number
  total_input_tokens: number
  total_output_tokens: number
  estimated_cost: number | null
  avg_session_duration: number | null
  avg_messages_per_session: number | null
  outcome_counts: Record<string, number>
  session_type_counts: Record<string, number>
  success_rate: number | null
  previous_period: OverviewStats | null
}

export interface FrictionReport {
  friction_type: string
  count: number
  details: string[]
}

export interface ToolRanking {
  tool_name: string
  total_calls: number
  session_count: number
}

export interface ModelRanking {
  model_name: string
  total_input_tokens: number
  total_output_tokens: number
  session_count: number
}

export interface Recommendation {
  category: string
  title: string
  description: string
  severity: string
  evidence: Record<string, unknown>
}

export interface DailyStatsResponse {
  date: string
  message_count: number
  session_count: number
  tool_call_count: number
  success_rate: number | null
}

export interface ModelCostBreakdown {
  model_name: string
  input_tokens: number
  output_tokens: number
  cache_read_tokens: number
  cache_creation_tokens: number
  estimated_cost: number
}

export interface DailyCostEntry {
  date: string
  estimated_cost: number
  session_count: number
}

export interface CostAnalytics {
  total_estimated_cost: number
  model_breakdown: ModelCostBreakdown[]
  daily_costs: DailyCostEntry[]
}

export interface EngineerStats {
  engineer_id: string
  name: string
  email: string
  team_id: string | null
  avatar_url: string | null
  github_username: string | null
  total_sessions: number
  total_tokens: number
  estimated_cost: number
  success_rate: number | null
  avg_duration: number | null
  top_tools: string[]
}

export interface EngineerAnalytics {
  engineers: EngineerStats[]
  total_count: number
}

export interface ProjectStats {
  project_name: string
  total_sessions: number
  unique_engineers: number
  total_tokens: number
  estimated_cost: number
  outcome_distribution: Record<string, number>
  top_tools: string[]
}

export interface ProjectAnalytics {
  projects: ProjectStats[]
  total_count: number
}

export interface HeatmapCell {
  day_of_week: number
  hour: number
  count: number
}

export interface ActivityHeatmap {
  cells: HeatmapCell[]
  max_count: number
}

export interface SessionMessage {
  ordinal: number
  role: "human" | "assistant" | "tool_result"
  content_text: string | null
  tool_calls: { name: string; input_preview: string }[] | null
  tool_results: { name: string; output_preview: string }[] | null
  token_count: number | null
  model: string | null
}

export interface ProductivityMetrics {
  sessions_per_engineer_per_day: number
  avg_cost_per_session: number | null
  cost_per_successful_outcome: number | null
  estimated_time_saved_hours: number | null
  estimated_value_created: number | null
  adoption_rate: number
  power_users: number
  total_engineers_in_scope: number
  total_cost: number
  roi_ratio: number | null
}

export interface BenchmarkContext {
  team_avg_sessions: number
  team_avg_tokens: number
  team_avg_cost: number
  team_avg_success_rate: number
  team_avg_duration: number | null
}

export interface EngineerBenchmark {
  engineer_id: string
  name: string
  display_name: string | null
  avatar_url: string | null
  total_sessions: number
  total_tokens: number
  estimated_cost: number
  success_rate: number | null
  avg_duration: number | null
  percentile_sessions: number
  percentile_tokens: number
  percentile_cost: number
  vs_team_avg: Record<string, number>
}

export interface EngineerBenchmarkResponse {
  engineers: EngineerBenchmark[]
  benchmark: BenchmarkContext
}

export interface AlertResponse {
  id: string
  team_id: string | null
  engineer_id: string | null
  alert_type: string
  severity: string
  title: string
  message: string
  metric_name: string
  expected_value: number | null
  actual_value: number | null
  threshold: number | null
  detected_at: string
  acknowledged_at: string | null
  dismissed: boolean
}

export interface SystemStats {
  total_engineers: number
  active_engineers: number
  total_teams: number
  total_sessions: number
  total_ingest_events: number
  database_type: string
}

export interface IngestEventResponse {
  id: number
  engineer_id: string
  event_type: string
  session_id: string | null
  payload_size_bytes: number | null
  status: string
  error_message: string | null
  created_at: string
}
