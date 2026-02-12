export interface TeamResponse {
  id: string
  name: string
  created_at: string
}

export interface EngineerResponse {
  id: string
  name: string
  email: string
  team_id: string | null
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
  avg_session_duration: number | null
  avg_messages_per_session: number | null
  outcome_counts: Record<string, number>
  session_type_counts: Record<string, number>
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
}
