from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

AgentType = Literal["claude_code", "codex_cli", "gemini_cli"]

# --- Team ---


class TeamCreate(BaseModel):
    name: str


class TeamResponse(BaseModel):
    id: str
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Engineer ---


class EngineerCreate(BaseModel):
    name: str
    email: str
    team_id: str | None = None


class EngineerResponse(BaseModel):
    id: str
    name: str
    email: str
    team_id: str | None
    role: str = "engineer"
    is_active: bool = True
    avatar_url: str | None = None
    github_username: str | None = None
    display_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EngineerUpdate(BaseModel):
    role: str | None = None
    team_id: str | None = None
    is_active: bool | None = None
    github_id: int | None = None
    github_username: str | None = None
    avatar_url: str | None = None
    display_name: str | None = None


class EngineerCreateResponse(BaseModel):
    engineer: EngineerResponse
    api_key: str = Field(description="Store this key securely; it cannot be retrieved again.")


# --- Session Facets ---


class SessionFacetsPayload(BaseModel):
    underlying_goal: str | None = None
    goal_categories: list[str] | None = None
    outcome: str | None = None
    session_type: str | None = None
    primary_success: str | None = None
    agent_helpfulness: str | None = None
    brief_summary: str | None = None
    user_satisfaction_counts: dict[str, int] | None = None
    friction_counts: dict[str, int] | None = None
    friction_detail: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _accept_claude_helpfulness(cls, data: dict) -> dict:
        if isinstance(data, dict) and "claude_helpfulness" in data:
            data.setdefault("agent_helpfulness", data.pop("claude_helpfulness"))
        return data


class SessionFacetsResponse(BaseModel):
    underlying_goal: str | None
    goal_categories: list[str] | None
    outcome: str | None
    session_type: str | None
    primary_success: str | None
    agent_helpfulness: str | None
    brief_summary: str | None
    user_satisfaction_counts: dict[str, int] | None
    friction_counts: dict[str, int] | None
    friction_detail: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Tool / Model Usage ---


class ToolUsagePayload(BaseModel):
    tool_name: str
    call_count: int


class ModelUsagePayload(BaseModel):
    model_name: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0


class ToolUsageResponse(BaseModel):
    tool_name: str
    call_count: int

    model_config = {"from_attributes": True}


class ModelUsageResponse(BaseModel):
    model_name: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int

    model_config = {"from_attributes": True}


# --- Session Messages ---


class SessionMessagePayload(BaseModel):
    ordinal: int
    role: str
    content_text: str | None = None
    tool_calls: list[dict] | None = None
    tool_results: list[dict] | None = None
    token_count: int | None = None
    model: str | None = None


class SessionMessageResponse(BaseModel):
    ordinal: int
    role: str
    content_text: str | None
    tool_calls: list[dict] | None
    tool_results: list[dict] | None
    token_count: int | None
    model: str | None

    model_config = {"from_attributes": True}


# --- Session Ingest ---


class CommitPayload(BaseModel):
    sha: str
    message: str | None = None
    author_name: str | None = None
    author_email: str | None = None
    committed_at: datetime | None = None
    files_changed: int = 0
    lines_added: int = 0
    lines_deleted: int = 0


class SessionIngestPayload(BaseModel):
    session_id: str
    api_key: str
    agent_type: AgentType = "claude_code"
    project_path: str | None = None
    project_name: str | None = None
    git_branch: str | None = None
    agent_version: str | None = None
    permission_mode: str | None = None
    end_reason: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: float | None = None
    message_count: int = 0
    user_message_count: int = 0
    assistant_message_count: int = 0
    tool_call_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    primary_model: str | None = None
    first_prompt: str | None = None
    summary: str | None = None
    facets: SessionFacetsPayload | None = None
    tool_usages: list[ToolUsagePayload] = []
    model_usages: list[ModelUsagePayload] = []
    messages: list[SessionMessagePayload] = []
    git_remote_url: str | None = None
    commits: list[CommitPayload] = []

    @model_validator(mode="before")
    @classmethod
    def _accept_claude_version(cls, data: dict) -> dict:
        if isinstance(data, dict) and "claude_version" in data:
            data.setdefault("agent_version", data.pop("claude_version"))
        return data


class BulkIngestPayload(BaseModel):
    api_key: str
    sessions: list[SessionIngestPayload]


class IngestResponse(BaseModel):
    status: str
    session_id: str
    created: bool


class BulkIngestResponse(BaseModel):
    status: str
    results: list[IngestResponse]


# --- Session Response ---


class SessionResponse(BaseModel):
    id: str
    engineer_id: str
    agent_type: str = "claude_code"
    project_path: str | None
    project_name: str | None
    git_branch: str | None
    agent_version: str | None
    permission_mode: str | None
    end_reason: str | None
    started_at: datetime | None
    ended_at: datetime | None
    duration_seconds: float | None
    message_count: int
    user_message_count: int
    assistant_message_count: int
    tool_call_count: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int
    primary_model: str | None
    first_prompt: str | None
    summary: str | None
    has_facets: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionDetailResponse(SessionResponse):
    facets: SessionFacetsResponse | None = None
    tool_usages: list[ToolUsageResponse] = []
    model_usages: list[ModelUsageResponse] = []


# --- Analytics ---


class OverviewStats(BaseModel):
    total_sessions: int
    total_engineers: int
    total_messages: int
    total_tool_calls: int
    total_input_tokens: int
    total_output_tokens: int
    estimated_cost: float | None = None
    avg_session_duration: float | None
    avg_messages_per_session: float | None
    outcome_counts: dict[str, int]
    session_type_counts: dict[str, int]
    success_rate: float | None = None
    previous_period: "OverviewStats | None" = None
    end_reason_counts: dict[str, int] = {}
    cache_hit_rate: float | None = None
    avg_health_score: float | None = None
    agent_type_counts: dict[str, int] = {}


class FrictionReport(BaseModel):
    friction_type: str
    count: int
    details: list[str]


class ToolRanking(BaseModel):
    tool_name: str
    total_calls: int
    session_count: int


class ModelRanking(BaseModel):
    model_name: str
    total_input_tokens: int
    total_output_tokens: int
    session_count: int


class Recommendation(BaseModel):
    category: str
    title: str
    description: str
    severity: str  # info, warning, critical
    evidence: dict


# --- Daily Stats ---


class DailyStatsResponse(BaseModel):
    date: date
    message_count: int
    session_count: int
    tool_call_count: int
    success_rate: float | None = None

    model_config = {"from_attributes": True}


# --- Cost Analytics ---


class ModelCostBreakdown(BaseModel):
    model_name: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int
    estimated_cost: float


class DailyCostEntry(BaseModel):
    date: date
    estimated_cost: float
    session_count: int


class CostAnalytics(BaseModel):
    total_estimated_cost: float
    model_breakdown: list[ModelCostBreakdown]
    daily_costs: list[DailyCostEntry]


# --- Engineer Analytics ---


class EngineerStats(BaseModel):
    engineer_id: str
    name: str
    email: str
    team_id: str | None
    avatar_url: str | None = None
    github_username: str | None = None
    total_sessions: int
    total_tokens: int
    estimated_cost: float
    success_rate: float | None = None
    avg_duration: float | None = None
    top_tools: list[str] = []


class EngineerAnalytics(BaseModel):
    engineers: list[EngineerStats]
    total_count: int


# --- Project Analytics ---


class ProjectStats(BaseModel):
    project_name: str
    total_sessions: int
    unique_engineers: int
    total_tokens: int
    estimated_cost: float
    outcome_distribution: dict[str, int] = {}
    top_tools: list[str] = []


class ProjectAnalytics(BaseModel):
    projects: list[ProjectStats]
    total_count: int


# --- Activity Heatmap ---


class HeatmapCell(BaseModel):
    day_of_week: int  # 0=Monday, 6=Sunday
    hour: int  # 0-23
    count: int


class ActivityHeatmap(BaseModel):
    cells: list[HeatmapCell]
    max_count: int


# --- Productivity Metrics ---


class ProductivityMetrics(BaseModel):
    sessions_per_engineer_per_day: float
    avg_cost_per_session: float | None
    cost_per_successful_outcome: float | None
    estimated_time_saved_hours: float | None
    estimated_value_created: float | None
    adoption_rate: float
    power_users: int
    total_engineers_in_scope: int
    total_cost: float
    roi_ratio: float | None


# --- Peer Benchmarking ---


class BenchmarkContext(BaseModel):
    team_avg_sessions: float
    team_avg_tokens: float
    team_avg_cost: float
    team_avg_success_rate: float
    team_avg_duration: float | None


class EngineerBenchmark(BaseModel):
    engineer_id: str
    name: str
    display_name: str | None = None
    avatar_url: str | None = None
    total_sessions: int
    total_tokens: int
    estimated_cost: float
    success_rate: float | None
    avg_duration: float | None
    percentile_sessions: int
    percentile_tokens: int
    percentile_cost: int
    vs_team_avg: dict[str, float]


class EngineerBenchmarkResponse(BaseModel):
    engineers: list[EngineerBenchmark]
    benchmark: BenchmarkContext


# --- Alerts ---


class AlertResponse(BaseModel):
    id: str
    team_id: str | None
    engineer_id: str | None
    alert_type: str
    severity: str
    title: str
    message: str
    metric_name: str
    expected_value: float | None
    actual_value: float | None
    threshold: float | None
    detected_at: datetime
    acknowledged_at: datetime | None
    dismissed: bool

    model_config = {"from_attributes": True}


class DetectionResult(BaseModel):
    alerts_created: int
    alert_ids: list[str]


# --- Alert Config ---


class AlertConfigCreate(BaseModel):
    team_id: str | None = None
    alert_type: str
    enabled: bool = True
    threshold: float


class AlertConfigUpdate(BaseModel):
    enabled: bool | None = None
    threshold: float | None = None


class AlertConfigResponse(BaseModel):
    id: str
    team_id: str | None
    alert_type: str
    enabled: bool
    threshold: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AlertThresholds(BaseModel):
    friction_spike_multiplier: float
    usage_drop_ratio: float
    cost_spike_warning: float
    cost_spike_critical: float
    success_rate_drop_pp: float


# --- Admin ---


class SystemStats(BaseModel):
    total_engineers: int
    active_engineers: int
    total_teams: int
    total_sessions: int
    total_ingest_events: int
    database_type: str


class IngestEventResponse(BaseModel):
    id: int
    engineer_id: str
    event_type: str
    session_id: str | None
    payload_size_bytes: int | None
    status: str
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Audit Log ---


# --- Bottleneck Analytics ---


class FrictionImpact(BaseModel):
    friction_type: str
    occurrence_count: int
    sessions_affected: int
    success_rate_with: float | None
    success_rate_without: float | None
    impact_score: float | None
    sample_details: list[str]


class ProjectFriction(BaseModel):
    project_name: str
    total_sessions: int
    sessions_with_friction: int
    friction_rate: float
    top_friction_types: list[str]
    total_friction_count: int


class FrictionTrend(BaseModel):
    date: date
    total_friction_count: int
    sessions_with_friction: int
    total_sessions: int


class BottleneckAnalytics(BaseModel):
    friction_impacts: list[FrictionImpact]
    project_friction: list[ProjectFriction]
    friction_trends: list[FrictionTrend]
    total_sessions_analyzed: int
    sessions_with_any_friction: int
    overall_friction_rate: float


class AuditLogResponse(BaseModel):
    id: int
    actor_id: str | None
    actor_role: str
    action: str
    resource_type: str
    resource_id: str | None
    details: dict | None
    ip_address: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Tool Adoption Analytics ---


class ToolAdoptionEntry(BaseModel):
    tool_name: str
    total_calls: int
    session_count: int
    engineer_count: int
    adoption_rate: float
    avg_calls_per_session: float


class ToolTrendEntry(BaseModel):
    date: date
    tool_name: str
    call_count: int
    session_count: int


class EngineerToolProfile(BaseModel):
    engineer_id: str
    name: str
    tools_used: int
    total_tool_calls: int
    top_tools: list[str]


class ToolAdoptionAnalytics(BaseModel):
    tool_adoption: list[ToolAdoptionEntry]
    tool_trends: list[ToolTrendEntry]
    engineer_profiles: list[EngineerToolProfile]
    total_engineers: int
    total_tools_discovered: int
    avg_tools_per_engineer: float


# --- Config Optimization ---


class ConfigSuggestion(BaseModel):
    category: str  # "hook", "permission", "model", "mcp", "workflow"
    title: str
    description: str
    severity: str  # "info", "warning"
    evidence: dict
    suggested_config: str | None = None


class ConfigOptimizationResponse(BaseModel):
    suggestions: list[ConfigSuggestion]
    sessions_analyzed: int


# --- Personalized Tips ---


class PersonalizedTip(BaseModel):
    category: str  # "tool_gap", "diversity", "friction", "success", "workflow"
    title: str
    description: str
    severity: str
    evidence: dict


class PersonalizedTipsResponse(BaseModel):
    tips: list[PersonalizedTip]
    sessions_analyzed: int
    engineer_id: str | None = None


# --- Skill Inventory ---


class EngineerSkillProfile(BaseModel):
    engineer_id: str
    name: str
    session_types: dict[str, int]
    tool_proficiency: dict[str, str]
    project_count: int
    total_sessions: int
    diversity_score: float


class TeamSkillGap(BaseModel):
    skill: str
    coverage_pct: float
    total_engineers: int
    engineers_with_skill: int


class SkillInventoryResponse(BaseModel):
    engineer_profiles: list[EngineerSkillProfile]
    team_skill_gaps: list[TeamSkillGap]
    total_engineers: int
    total_session_types: int
    total_tools_used: int


# --- Learning Paths ---


class LearningRecommendation(BaseModel):
    category: str  # "session_type_gap", "tool_gap", "complexity", "goal_gap"
    skill_area: str
    title: str
    description: str
    priority: str  # "high", "medium", "low"
    evidence: dict


class EngineerLearningPath(BaseModel):
    engineer_id: str
    name: str
    total_sessions: int
    recommendations: list[LearningRecommendation]
    coverage_score: float
    complexity_trend: str  # "increasing", "flat", "decreasing"


class LearningPathsResponse(BaseModel):
    engineer_paths: list[EngineerLearningPath]
    team_skill_universe: dict[str, int]
    sessions_analyzed: int


# --- Pattern Sharing ---


class EngineerApproach(BaseModel):
    engineer_id: str
    name: str
    session_id: str
    duration_seconds: float | None
    tool_count: int
    outcome: str | None
    helpfulness: str | None
    tools_used: list[str]


class SharedPattern(BaseModel):
    cluster_id: str
    cluster_type: str  # "session_type", "goal_category", "project"
    cluster_label: str
    session_count: int
    engineer_count: int
    approaches: list[EngineerApproach]
    best_approach: EngineerApproach | None
    avg_duration: float | None
    success_rate: float | None
    insight: str


class PatternSharingResponse(BaseModel):
    patterns: list[SharedPattern]
    total_clusters_found: int
    sessions_analyzed: int


# --- Onboarding Acceleration ---


class CohortMetrics(BaseModel):
    cohort_label: str  # "new_hire", "ramping", "experienced"
    engineer_count: int
    avg_sessions_per_engineer: float
    avg_tool_diversity: float
    avg_duration_seconds: float | None
    success_rate: float | None
    avg_friction_rate: float
    top_tools: list[str]
    top_session_types: list[str]


class NewHireProgress(BaseModel):
    engineer_id: str
    name: str
    days_since_first_session: int
    total_sessions: int
    tool_diversity: int
    success_rate: float | None
    avg_duration: float | None
    friction_rate: float
    velocity_score: float
    lagging_areas: list[str]


class OnboardingRecommendation(BaseModel):
    category: str  # "tool_adoption", "complexity", "mentoring", "friction"
    title: str
    description: str
    target_engineer_id: str | None
    evidence: dict


class OnboardingAccelerationResponse(BaseModel):
    cohorts: list[CohortMetrics]
    new_hire_progress: list[NewHireProgress]
    recommendations: list[OnboardingRecommendation]
    sessions_analyzed: int
    experienced_benchmark: CohortMetrics | None


# --- Quality Metrics ---


class QualityOverview(BaseModel):
    sessions_with_commits: int
    total_commits: int
    total_lines_added: int
    total_lines_deleted: int
    total_prs: int
    pr_merge_rate: float | None
    avg_commits_per_session: float | None
    avg_lines_per_session: float | None
    avg_review_comments_per_pr: float | None
    avg_time_to_merge_hours: float | None


class DailyCodeVolume(BaseModel):
    date: str
    lines_added: int
    lines_deleted: int
    commits: int
    sessions: int


class QualityByType(BaseModel):
    session_type: str
    session_count: int
    avg_commits: float
    avg_lines_added: float
    avg_lines_deleted: float
    pr_count: int
    merge_rate: float | None


class EngineerQuality(BaseModel):
    engineer_id: str
    name: str
    sessions_with_commits: int
    total_commits: int
    total_lines_added: int
    total_lines_deleted: int
    pr_count: int
    merge_rate: float | None
    avg_review_comments: float | None


class PRSummary(BaseModel):
    repository: str
    pr_number: int
    title: str | None
    state: str
    head_branch: str | None
    additions: int
    deletions: int
    review_comments_count: int
    author: str | None
    linked_sessions: int
    pr_created_at: str | None
    merged_at: str | None


class QualityMetricsResponse(BaseModel):
    overview: QualityOverview
    daily_volume: list[DailyCodeVolume]
    by_session_type: list[QualityByType]
    engineer_quality: list[EngineerQuality]
    recent_prs: list[PRSummary]
    sessions_analyzed: int
    github_connected: bool


class GitHubSyncResponse(BaseModel):
    repos_synced: int
    prs_found: int
    commits_correlated: int


class GitHubStatusResponse(BaseModel):
    configured: bool
    app_id: int | None
    installation_id: int | None
    repos_count: int
    prs_count: int


# --- Session Insights ---


class EndReasonBreakdown(BaseModel):
    end_reason: str
    count: int
    avg_duration: float | None
    success_rate: float | None


class DailySatisfaction(BaseModel):
    date: date
    satisfied: int
    neutral: int
    dissatisfied: int


class SatisfactionSummary(BaseModel):
    total_sessions_with_data: int
    satisfied_count: int
    neutral_count: int
    dissatisfied_count: int
    satisfaction_rate: float | None
    trend: list[DailySatisfaction] = []


class FrictionCluster(BaseModel):
    cluster_label: str
    occurrence_count: int
    sample_details: list[str]


class DailyCacheEntry(BaseModel):
    date: date
    cache_read_tokens: int
    cache_creation_tokens: int
    input_tokens: int
    cache_hit_rate: float | None


class CacheEfficiencyMetrics(BaseModel):
    total_cache_read_tokens: int
    total_cache_creation_tokens: int
    total_input_tokens: int
    cache_hit_rate: float | None
    cache_savings_estimate: float | None
    daily_cache_trend: list[DailyCacheEntry] = []


class PermissionModeAnalysis(BaseModel):
    mode: str
    session_count: int
    success_rate: float | None
    avg_duration: float | None
    avg_friction_count: float | None


class DailyHealthEntry(BaseModel):
    date: date
    avg_score: float
    session_count: int


class SessionHealthDistribution(BaseModel):
    avg_score: float
    median_score: float
    buckets: dict[str, int]
    daily_trend: list[DailyHealthEntry] = []


class GoalTypeBreakdown(BaseModel):
    session_type: str
    count: int
    avg_cost: float | None
    success_rate: float | None
    avg_duration: float | None


class GoalCategoryBreakdown(BaseModel):
    category: str
    count: int
    avg_cost: float | None
    success_rate: float | None


class GoalAnalytics(BaseModel):
    session_type_breakdown: list[GoalTypeBreakdown]
    goal_category_breakdown: list[GoalCategoryBreakdown]


class PrimarySuccessAnalysis(BaseModel):
    full_count: int
    partial_count: int
    none_count: int
    unknown_count: int
    full_rate: float | None
    by_session_type: dict[str, dict[str, int]]


class SessionInsightsResponse(BaseModel):
    end_reasons: list[EndReasonBreakdown]
    satisfaction: SatisfactionSummary
    friction_clusters: list[FrictionCluster]
    cache_efficiency: CacheEfficiencyMetrics
    permission_modes: list[PermissionModeAnalysis]
    health_distribution: SessionHealthDistribution
    goals: GoalAnalytics
    primary_success: PrimarySuccessAnalysis
    sessions_analyzed: int


# --- Engineer Profile ---


class WeeklyMetricPoint(BaseModel):
    week: str  # "2026-W07"
    success_rate: float | None
    avg_duration: float | None
    tool_diversity: int
    estimated_cost: float
    session_count: int


class EngineerProfileResponse(BaseModel):
    engineer_id: str
    name: str
    email: str
    display_name: str | None = None
    team_id: str | None
    team_name: str | None = None
    avatar_url: str | None = None
    github_username: str | None = None
    created_at: str
    overview: OverviewStats
    weekly_trajectory: list[WeeklyMetricPoint]
    friction: list[FrictionReport]
    config_suggestions: list[ConfigSuggestion]
    strengths: SkillInventoryResponse
    learning_paths: list[EngineerLearningPath]
    quality: dict  # flexible dict for quality metrics
    leverage_score: float | None = None
    projects: list[str] = []
    tool_rankings: list[ToolRanking] = []


# --- Similar Sessions ---


class SimilarSession(BaseModel):
    session_id: str
    engineer_id: str
    engineer_name: str
    engineer_avatar_url: str | None = None
    project_name: str | None
    session_type: str | None
    outcome: str | None
    duration_seconds: float | None
    tools_used: list[str]
    similarity_reason: str  # "same_type_and_project" | "same_type" | "same_goal"
    started_at: str | None


class SimilarSessionsResponse(BaseModel):
    similar_sessions: list[SimilarSession]
    target_session_type: str | None
    target_project: str | None
    total_found: int


# --- Claude PR Comparison ---


class PRGroupMetrics(BaseModel):
    pr_count: int
    merge_rate: float | None
    avg_review_comments: float | None
    avg_time_to_merge_hours: float | None
    avg_additions: float | None
    avg_deletions: float | None


class ClaudePRComparisonResponse(BaseModel):
    claude_assisted: PRGroupMetrics
    non_claude: PRGroupMetrics
    delta_review_comments: float | None
    delta_merge_time_hours: float | None
    delta_merge_rate: float | None
    total_prs_analyzed: int


# --- Time to Team Average ---


class WeeklySuccessPoint(BaseModel):
    week_number: int  # weeks since first session
    success_rate: float | None
    session_count: int


class EngineerRampup(BaseModel):
    engineer_id: str
    name: str
    first_session_date: str
    weeks_to_team_average: int | None
    current_success_rate: float | None
    weekly_success_rates: list[WeeklySuccessPoint]


class TimeToTeamAverageResponse(BaseModel):
    engineers: list[EngineerRampup]
    team_avg_success_rate: float
    avg_weeks_to_match: float | None
    engineers_who_matched: int
    total_engineers: int


# --- AI DevEx Maturity ---


class ToolCategoryBreakdown(BaseModel):
    core: dict[str, int]
    search: dict[str, int]
    orchestration: dict[str, int]
    skill: dict[str, int]
    mcp: dict[str, int]


class EngineerLeverageProfile(BaseModel):
    engineer_id: str
    name: str
    leverage_score: float
    total_tool_calls: int
    orchestration_calls: int
    skill_calls: int
    mcp_calls: int
    top_agents: list[str]
    top_skills: list[str]
    category_distribution: dict[str, int]


class DailyLeverageEntry(BaseModel):
    date: str
    leverage_score: float
    total_calls: int


class AgentSkillUsage(BaseModel):
    name: str
    category: str
    total_calls: int
    session_count: int
    engineer_count: int


class ProjectReadinessEntry(BaseModel):
    repository: str
    has_claude_md: bool
    has_agents_md: bool
    has_claude_dir: bool
    ai_readiness_score: float
    session_count: int


class MaturityAnalyticsResponse(BaseModel):
    tool_categories: ToolCategoryBreakdown
    engineer_profiles: list[EngineerLeverageProfile]
    daily_leverage: list[DailyLeverageEntry]
    agent_skill_breakdown: list[AgentSkillUsage]
    project_readiness: list[ProjectReadinessEntry]
    sessions_analyzed: int
    avg_leverage_score: float
    orchestration_adoption_rate: float


# --- Narrative Insights ---


class NarrativeSection(BaseModel):
    title: str
    content: str


class NarrativeResponse(BaseModel):
    scope: str
    scope_label: str
    sections: list[NarrativeSection]
    generated_at: datetime
    cached: bool = False
    model_used: str
    data_summary: dict


class NarrativeStatusResponse(BaseModel):
    available: bool
    reason: str | None = None
