from datetime import date, datetime

from pydantic import BaseModel, Field

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
    claude_helpfulness: str | None = None
    brief_summary: str | None = None
    user_satisfaction_counts: dict[str, int] | None = None
    friction_counts: dict[str, int] | None = None
    friction_detail: str | None = None


class SessionFacetsResponse(BaseModel):
    underlying_goal: str | None
    goal_categories: list[str] | None
    outcome: str | None
    session_type: str | None
    primary_success: str | None
    claude_helpfulness: str | None
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


class SessionIngestPayload(BaseModel):
    session_id: str
    api_key: str
    project_path: str | None = None
    project_name: str | None = None
    git_branch: str | None = None
    claude_version: str | None = None
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
    project_path: str | None
    project_name: str | None
    git_branch: str | None
    claude_version: str | None
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
