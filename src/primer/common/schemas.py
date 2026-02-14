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
    avatar_url: str | None = None
    github_username: str | None = None
    display_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EngineerUpdate(BaseModel):
    role: str | None = None
    team_id: str | None = None


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
