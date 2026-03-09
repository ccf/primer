export interface PaginatedResponse<T> {
  items: T[]
  total_count: number
  limit: number
  offset: number
}

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

export type AgentType = 'claude_code' | 'codex_cli' | 'gemini_cli' | 'cursor'
export type TelemetryParity = 'required' | 'optional' | 'unavailable'

export interface SessionResponse {
  id: string
  engineer_id: string
  agent_type: AgentType
  project_path: string | null
  project_name: string | null
  git_branch: string | null
  agent_version: string | null
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
  agent_helpfulness: string | null
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
  end_reason_counts: Record<string, number>
  cache_hit_rate: number | null
  avg_health_score: number | null
  agent_type_counts: Record<string, number>
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

export interface AgentSourceQuality {
  agent_type: AgentType
  session_count: number
  transcript_parity: TelemetryParity
  transcript_coverage_pct: number
  tool_call_parity: TelemetryParity
  tool_call_coverage_pct: number
  model_usage_parity: TelemetryParity
  model_usage_coverage_pct: number
  facet_parity: TelemetryParity
  facet_coverage_pct: number
  native_discovery_parity: TelemetryParity
}

export interface RepositoryQuality {
  repository_full_name: string
  session_count: number
  sessions_with_commits: number
  sessions_with_linked_pull_requests: number
  github_sync_coverage_pct: number | null
  has_github_id: boolean
  has_default_branch: boolean
  metadata_coverage_pct: number
  readiness_checked: boolean
}

export interface MeasurementIntegrityStats {
  total_sessions: number
  sessions_with_messages: number
  sessions_with_facets: number
  facet_coverage_pct: number
  transcript_coverage_pct: number
  sessions_with_commit_sync_target: number
  sessions_with_linked_pull_requests: number
  github_sync_coverage_pct: number
  repositories_in_scope: number
  repositories_with_complete_metadata: number
  repositories_with_readiness_check: number
  repository_metadata_coverage_pct: number
  sessions_missing_transcript_telemetry: number
  sessions_missing_tool_telemetry: number
  sessions_missing_model_telemetry: number
  low_confidence_sessions: number
  missing_confidence_sessions: number
  legacy_outcome_sessions: number
  legacy_goal_category_sessions: number
  remaining_legacy_rows: number
  source_quality: AgentSourceQuality[]
  repository_quality: RepositoryQuality[]
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

export interface AlertConfigResponse {
  id: string
  team_id: string | null
  alert_type: string
  enabled: boolean
  threshold: number
  created_at: string
  updated_at: string
}

export interface AlertThresholds {
  friction_spike_multiplier: number
  usage_drop_ratio: number
  cost_spike_warning: number
  cost_spike_critical: number
  success_rate_drop_pp: number
}

export interface FrictionImpact {
  friction_type: string
  occurrence_count: number
  sessions_affected: number
  success_rate_with: number | null
  success_rate_without: number | null
  impact_score: number | null
  sample_details: string[]
}

export interface ProjectFriction {
  project_name: string
  total_sessions: number
  sessions_with_friction: number
  friction_rate: number
  top_friction_types: string[]
  total_friction_count: number
}

export interface FrictionTrend {
  date: string
  total_friction_count: number
  sessions_with_friction: number
  total_sessions: number
}

export interface BottleneckAnalytics {
  friction_impacts: FrictionImpact[]
  project_friction: ProjectFriction[]
  friction_trends: FrictionTrend[]
  total_sessions_analyzed: number
  sessions_with_any_friction: number
  overall_friction_rate: number
}

export interface AuditLogResponse {
  id: number
  actor_id: string | null
  actor_role: string
  action: string
  resource_type: string
  resource_id: string | null
  details: Record<string, unknown> | null
  ip_address: string | null
  created_at: string
}

export interface ToolAdoptionEntry {
  tool_name: string
  total_calls: number
  session_count: number
  engineer_count: number
  adoption_rate: number
  avg_calls_per_session: number
}

export interface ToolTrendEntry {
  date: string
  tool_name: string
  call_count: number
  session_count: number
}

export interface EngineerToolProfile {
  engineer_id: string
  name: string
  tools_used: number
  total_tool_calls: number
  top_tools: string[]
}

export interface ToolAdoptionAnalytics {
  tool_adoption: ToolAdoptionEntry[]
  tool_trends: ToolTrendEntry[]
  engineer_profiles: EngineerToolProfile[]
  total_engineers: number
  total_tools_discovered: number
  avg_tools_per_engineer: number
}

// --- Config Optimization ---

export interface ConfigSuggestion {
  category: string
  title: string
  description: string
  severity: string
  evidence: Record<string, unknown>
  suggested_config?: string | null
}

export interface ConfigOptimizationResponse {
  suggestions: ConfigSuggestion[]
  sessions_analyzed: number
}

// --- Personalized Tips ---

export interface PersonalizedTip {
  category: string
  title: string
  description: string
  severity: string
  evidence: Record<string, unknown>
}

export interface PersonalizedTipsResponse {
  tips: PersonalizedTip[]
  sessions_analyzed: number
  engineer_id?: string | null
}

// --- Skill Inventory ---

export interface EngineerSkillProfile {
  engineer_id: string
  name: string
  session_types: Record<string, number>
  tool_proficiency: Record<string, string>
  project_count: number
  total_sessions: number
  diversity_score: number
}

export interface TeamSkillGap {
  skill: string
  coverage_pct: number
  total_engineers: number
  engineers_with_skill: number
}

export interface SkillInventoryResponse {
  engineer_profiles: EngineerSkillProfile[]
  team_skill_gaps: TeamSkillGap[]
  total_engineers: number
  total_session_types: number
  total_tools_used: number
}

// --- Learning Paths ---

export interface LearningRecommendation {
  category: string
  skill_area: string
  title: string
  description: string
  priority: string
  evidence: Record<string, unknown>
}

export interface EngineerLearningPath {
  engineer_id: string
  name: string
  total_sessions: number
  recommendations: LearningRecommendation[]
  coverage_score: number
  complexity_trend: string
}

export interface LearningPathsResponse {
  engineer_paths: EngineerLearningPath[]
  team_skill_universe: Record<string, number>
  sessions_analyzed: number
}

// --- Pattern Sharing ---

export interface EngineerApproach {
  engineer_id: string
  name: string
  session_id: string
  duration_seconds: number | null
  tool_count: number
  outcome: string | null
  helpfulness: string | null
  tools_used: string[]
}

export interface SharedPattern {
  cluster_id: string
  cluster_type: string
  cluster_label: string
  session_count: number
  engineer_count: number
  approaches: EngineerApproach[]
  best_approach: EngineerApproach | null
  avg_duration: number | null
  success_rate: number | null
  insight: string
}

export interface PatternSharingResponse {
  patterns: SharedPattern[]
  total_clusters_found: number
  sessions_analyzed: number
}

// --- Onboarding Acceleration ---

export interface CohortMetrics {
  cohort_label: string
  engineer_count: number
  avg_sessions_per_engineer: number
  avg_tool_diversity: number
  avg_duration_seconds: number | null
  success_rate: number | null
  avg_friction_rate: number
  top_tools: string[]
  top_session_types: string[]
}

export interface NewHireProgress {
  engineer_id: string
  name: string
  days_since_first_session: number
  total_sessions: number
  tool_diversity: number
  success_rate: number | null
  avg_duration: number | null
  friction_rate: number
  velocity_score: number
  lagging_areas: string[]
}

export interface OnboardingRecommendation {
  category: string
  title: string
  description: string
  target_engineer_id: string | null
  evidence: Record<string, unknown>
}

export interface OnboardingAccelerationResponse {
  cohorts: CohortMetrics[]
  new_hire_progress: NewHireProgress[]
  recommendations: OnboardingRecommendation[]
  sessions_analyzed: number
  experienced_benchmark: CohortMetrics | null
}

// --- Quality Metrics ---

export interface QualityOverview {
  sessions_with_commits: number
  total_commits: number
  total_lines_added: number
  total_lines_deleted: number
  total_prs: number
  pr_merge_rate: number | null
  avg_commits_per_session: number | null
  avg_lines_per_session: number | null
  avg_review_comments_per_pr: number | null
  avg_time_to_merge_hours: number | null
}

export interface DailyCodeVolume {
  date: string
  lines_added: number
  lines_deleted: number
  commits: number
  sessions: number
}

export interface QualityByType {
  session_type: string
  session_count: number
  avg_commits: number
  avg_lines_added: number
  avg_lines_deleted: number
  pr_count: number
  merge_rate: number | null
}

export interface EngineerQuality {
  engineer_id: string
  name: string
  sessions_with_commits: number
  total_commits: number
  total_lines_added: number
  total_lines_deleted: number
  pr_count: number
  merge_rate: number | null
  avg_review_comments: number | null
}

export interface QualityAttributionRow {
  dimension: string
  label: string
  linked_sessions: number
  linked_prs: number
  merge_rate: number | null
  avg_review_comments_per_pr: number | null
  avg_findings_per_pr: number | null
  high_severity_findings_per_pr: number | null
  avg_time_to_merge_hours: number | null
  findings_fix_rate: number | null
}

export interface PRSummary {
  repository: string
  pr_number: number
  title: string | null
  state: string
  head_branch: string | null
  additions: number
  deletions: number
  review_comments_count: number
  author: string | null
  linked_sessions: number
  pr_created_at: string | null
  merged_at: string | null
}

export interface ReviewFindingSummary {
  id: string
  source: string
  severity: string
  title: string
  description: string | null
  file_path: string | null
  line_number: number | null
  status: string
  detected_at: string
  resolved_at: string | null
  pr_number: number | null
  repository: string | null
}

export interface FindingsOverview {
  total_findings: number
  by_severity: Record<string, number>
  by_source: Record<string, number>
  fix_rate: number | null
  avg_findings_per_pr: number | null
  findings_trend: { date: string; count: number }[]
}

export interface QualityMetricsResponse {
  overview: QualityOverview
  daily_volume: DailyCodeVolume[]
  by_session_type: QualityByType[]
  engineer_quality: EngineerQuality[]
  attribution: QualityAttributionRow[]
  recent_prs: PRSummary[]
  findings_overview: FindingsOverview | null
  sessions_analyzed: number
  github_connected: boolean
}

export interface GitHubStatusResponse {
  configured: boolean
  app_id: number | null
  installation_id: number | null
  repos_count: number
  prs_count: number
}

// --- Session Insights ---

export interface EndReasonBreakdown {
  end_reason: string
  count: number
  avg_duration: number | null
  success_rate: number | null
}

export interface DailySatisfaction {
  date: string
  satisfied: number
  neutral: number
  dissatisfied: number
}

export interface SatisfactionSummary {
  total_sessions_with_data: number
  satisfied_count: number
  neutral_count: number
  dissatisfied_count: number
  satisfaction_rate: number | null
  trend: DailySatisfaction[]
}

export interface FrictionCluster {
  cluster_label: string
  occurrence_count: number
  sample_details: string[]
}

export interface DailyCacheEntry {
  date: string
  cache_read_tokens: number
  cache_creation_tokens: number
  input_tokens: number
  cache_hit_rate: number | null
}

export interface CacheEfficiencyMetrics {
  total_cache_read_tokens: number
  total_cache_creation_tokens: number
  total_input_tokens: number
  cache_hit_rate: number | null
  cache_savings_estimate: number | null
  daily_cache_trend: DailyCacheEntry[]
}

export interface PermissionModeAnalysis {
  mode: string
  session_count: number
  success_rate: number | null
  avg_duration: number | null
  avg_friction_count: number | null
}

export interface DailyHealthEntry {
  date: string
  avg_score: number
  session_count: number
}

export interface SessionHealthDistribution {
  avg_score: number
  median_score: number
  buckets: Record<string, number>
  daily_trend: DailyHealthEntry[]
}

export interface GoalTypeBreakdown {
  session_type: string
  count: number
  avg_cost: number | null
  success_rate: number | null
  avg_duration: number | null
}

export interface GoalCategoryBreakdown {
  category: string
  count: number
  avg_cost: number | null
  success_rate: number | null
}

export interface GoalAnalytics {
  session_type_breakdown: GoalTypeBreakdown[]
  goal_category_breakdown: GoalCategoryBreakdown[]
}

export interface PrimarySuccessAnalysis {
  full_count: number
  partial_count: number
  none_count: number
  unknown_count: number
  full_rate: number | null
  by_session_type: Record<string, Record<string, number>>
}

export interface SessionInsightsResponse {
  end_reasons: EndReasonBreakdown[]
  satisfaction: SatisfactionSummary
  friction_clusters: FrictionCluster[]
  cache_efficiency: CacheEfficiencyMetrics
  permission_modes: PermissionModeAnalysis[]
  health_distribution: SessionHealthDistribution
  goals: GoalAnalytics
  primary_success: PrimarySuccessAnalysis
  sessions_analyzed: number
}

// --- Engineer Profile ---

export interface WeeklyMetricPoint {
  week: string
  success_rate: number | null
  avg_duration: number | null
  tool_diversity: number
  estimated_cost: number
  session_count: number
}

export interface EngineerProfileResponse {
  engineer_id: string
  name: string
  email: string
  display_name: string | null
  team_id: string | null
  team_name: string | null
  avatar_url: string | null
  github_username: string | null
  created_at: string
  overview: OverviewStats
  weekly_trajectory: WeeklyMetricPoint[]
  friction: FrictionReport[]
  config_suggestions: ConfigSuggestion[]
  strengths: SkillInventoryResponse
  learning_paths: EngineerLearningPath[]
  quality: Record<string, unknown>
  leverage_score: number | null
  projects: string[]
  tool_rankings: ToolRanking[]
}

// --- Similar Sessions ---

export interface SimilarSession {
  session_id: string
  engineer_id: string
  engineer_name: string
  engineer_avatar_url: string | null
  project_name: string | null
  session_type: string | null
  outcome: string | null
  duration_seconds: number | null
  tools_used: string[]
  similarity_reason: string
  started_at: string | null
}

export interface SimilarSessionsResponse {
  similar_sessions: SimilarSession[]
  target_session_type: string | null
  target_project: string | null
  total_found: number
}

// --- Claude PR Comparison ---

export interface PRGroupMetrics {
  pr_count: number
  merge_rate: number | null
  avg_review_comments: number | null
  avg_time_to_merge_hours: number | null
  avg_additions: number | null
  avg_deletions: number | null
}

export interface ClaudePRComparisonResponse {
  claude_assisted: PRGroupMetrics
  non_claude: PRGroupMetrics
  delta_review_comments: number | null
  delta_merge_time_hours: number | null
  delta_merge_rate: number | null
  total_prs_analyzed: number
}

// --- Time to Team Average ---

export interface WeeklySuccessPoint {
  week_number: number
  success_rate: number | null
  session_count: number
}

export interface EngineerRampup {
  engineer_id: string
  name: string
  first_session_date: string
  weeks_to_team_average: number | null
  current_success_rate: number | null
  weekly_success_rates: WeeklySuccessPoint[]
}

export interface TimeToTeamAverageResponse {
  engineers: EngineerRampup[]
  team_avg_success_rate: number
  avg_weeks_to_match: number | null
  engineers_who_matched: number
  total_engineers: number
}

// --- AI DevEx Maturity ---

export interface ToolCategoryBreakdown {
  core: Record<string, number>
  search: Record<string, number>
  orchestration: Record<string, number>
  skill: Record<string, number>
  mcp: Record<string, number>
}

export interface LeverageBreakdown {
  tool_diversity: number
  category_spread: number
  tool_mastery: number
  orch_skill_ratio: number
  agent_team_score: number
  orchestration_depth: number
  cache_efficiency: number
  model_diversity: number
  efficiency: number
}

export interface EngineerLeverageProfile {
  engineer_id: string
  name: string
  leverage_score: number
  effectiveness_score: number | null
  leverage_breakdown: LeverageBreakdown | null
  total_tool_calls: number
  orchestration_calls: number
  skill_calls: number
  mcp_calls: number
  model_count: number
  cost_tier_count: number
  uses_agent_teams: boolean
  top_agents: string[]
  top_skills: string[]
  top_models: string[]
  category_distribution: Record<string, number>
}

export interface DailyLeverageEntry {
  date: string
  leverage_score: number
  total_calls: number
}

export interface AgentSkillUsage {
  name: string
  category: string
  total_calls: number
  session_count: number
  engineer_count: number
}

export interface ProjectReadinessEntry {
  repository: string
  has_claude_md: boolean
  has_agents_md: boolean
  has_claude_dir: boolean
  ai_readiness_score: number
  session_count: number
}

export interface MaturityAnalyticsResponse {
  tool_categories: ToolCategoryBreakdown
  engineer_profiles: EngineerLeverageProfile[]
  daily_leverage: DailyLeverageEntry[]
  agent_skill_breakdown: AgentSkillUsage[]
  project_readiness: ProjectReadinessEntry[]
  sessions_analyzed: number
  avg_leverage_score: number
  avg_effectiveness_score: number | null
  orchestration_adoption_rate: number
  team_orchestration_adoption_rate: number
  model_diversity_avg: number
}

// --- Narrative Insights ---

export interface NarrativeSection {
  title: string
  content: string
}

export interface NarrativeResponse {
  scope: string
  scope_label: string
  sections: NarrativeSection[]
  generated_at: string
  cached: boolean
  model_used: string
  data_summary: Record<string, unknown>
}

export interface NarrativeStatusResponse {
  available: boolean
  reason: string | null
}

// --- FinOps ---

export interface ModelCacheBreakdown {
  model_name: string
  cache_read_tokens: number
  cache_creation_tokens: number
  input_tokens: number
  cache_hit_rate: number | null
  estimated_savings: number
}

export interface EngineerCacheEfficiency {
  engineer_id: string
  engineer_name: string
  cache_hit_rate: number | null
  estimated_savings: number
  potential_additional_savings: number
  total_cache_read_tokens: number
  total_input_tokens: number
}

export interface CacheAnalyticsResponse {
  total_cache_read_tokens: number
  total_cache_creation_tokens: number
  total_input_tokens: number
  cache_hit_rate: number | null
  cache_savings_estimate: number | null
  daily_cache_trend: DailyCacheEntry[]
  model_cache_breakdown: ModelCacheBreakdown[]
  engineer_cache_breakdown: EngineerCacheEfficiency[]
  total_potential_additional_savings: number
}

export interface PlanTier {
  name: string
  label: string
  monthly_cost: number
}

export interface EngineerCostComparison {
  engineer_id: string
  engineer_name: string
  monthly_api_cost: number
  recommended_plan: string
  recommended_plan_cost: number
  savings_vs_api: number
  current_billing_mode: string | null
  daily_avg_cost: number
}

export interface PlanAllocationSummary {
  plan: string
  label: string
  monthly_cost_per_seat: number
  engineer_count: number
  total_monthly_cost: number
}

export interface CostModelingResponse {
  period_days: number
  plan_tiers: PlanTier[]
  engineers: EngineerCostComparison[]
  allocation: PlanAllocationSummary[]
  total_api_cost_monthly: number
  total_optimal_cost_monthly: number
  total_savings_monthly: number
}

export interface ForecastPoint {
  date: string
  projected_cost: number
  upper_bound: number
  lower_bound: number
}

export interface CostForecastResponse {
  historical: DailyCostEntry[]
  forecast: ForecastPoint[]
  monthly_projection: number
  trend_direction: string
}

export interface BudgetStatus {
  id: string
  name: string
  team_id: string | null
  team_name: string | null
  amount: number
  period: string
  current_spend: number
  burn_rate_daily: number
  projected_end_of_period: number
  alert_threshold_pct: number
  pct_used: number
  status: string
}
