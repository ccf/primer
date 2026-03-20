from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from primer.common.facet_taxonomy import (
    canonical_outcome,
    normalize_goal_categories,
    validate_inbound_goal_categories,
    validate_inbound_outcome,
)


class PaginatedResponse[T](BaseModel):
    items: list[T]
    total_count: int
    limit: int
    offset: int


AgentType = Literal["claude_code", "codex_cli", "gemini_cli", "cursor"]
TelemetryParity = Literal["required", "optional", "unavailable"]
InterventionStatus = Literal["planned", "in_progress", "completed", "dismissed"]
ExecutionEvidenceType = Literal["test", "lint", "build", "verification"]
ExecutionEvidenceStatus = Literal["passed", "failed", "unknown"]
WorkflowStep = Literal[
    "search",
    "read",
    "edit",
    "execute",
    "test",
    "fix",
    "delegate",
    "integrate",
    "ship",
]
SessionArchetype = Literal[
    "debugging",
    "feature_delivery",
    "refactor",
    "migration",
    "docs",
    "investigation",
]
ArchetypeSource = Literal["session_type", "heuristic"]
DelegationEdgeType = Literal[
    "subagent_task",
    "agent_spawn",
    "team_setup",
    "team_message",
    "worktree_handoff",
]
RecoveryStrategy = Literal[
    "inspect_context",
    "edit_fix",
    "revert_or_reset",
    "rerun_verification",
    "delegate_or_parallelize",
]
RecoveryResult = Literal["recovered", "abandoned", "unresolved"]
CustomizationType = Literal["mcp", "subagent", "skill", "command", "template"]
CustomizationState = Literal["available", "enabled", "invoked"]
CustomizationProvenance = Literal[
    "built_in",
    "user_local",
    "repo_defined",
    "org_managed",
    "marketplace",
    "unknown",
]
CustomizationSourceClassification = Literal["built_in", "marketplace", "custom", "unknown"]

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
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
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

    @field_validator("goal_categories", mode="before")
    @classmethod
    def _normalize_goal_categories(cls, value: object) -> list[str] | None:
        return validate_inbound_goal_categories(value)

    @field_validator("outcome", mode="before")
    @classmethod
    def _normalize_outcome(cls, value: object) -> str | None:
        return validate_inbound_outcome(value)

    @field_validator("confidence_score", mode="before")
    @classmethod
    def _reject_boolean_confidence_score(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("confidence_score must be numeric, not boolean")
        return value


class SessionFacetsResponse(BaseModel):
    underlying_goal: str | None
    goal_categories: list[str] | None
    outcome: str | None
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    session_type: str | None
    primary_success: str | None
    agent_helpfulness: str | None
    brief_summary: str | None
    user_satisfaction_counts: dict[str, int] | None
    friction_counts: dict[str, int] | None
    friction_detail: str | None
    created_at: datetime

    @field_validator("goal_categories", mode="before")
    @classmethod
    def _normalize_goal_categories(cls, value: object) -> list[str] | None:
        return normalize_goal_categories(value)

    @field_validator("outcome", mode="before")
    @classmethod
    def _normalize_outcome(cls, value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return canonical_outcome(value)
        return value

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


class SessionCustomizationResponse(BaseModel):
    customization_type: CustomizationType
    state: CustomizationState
    identifier: str
    provenance: CustomizationProvenance
    source_classification: CustomizationSourceClassification
    display_name: str | None
    source_path: str | None
    invocation_count: int
    details: dict[str, Any] | None

    model_config = {"from_attributes": True}


class SessionExecutionEvidenceResponse(BaseModel):
    ordinal: int
    evidence_type: ExecutionEvidenceType
    status: ExecutionEvidenceStatus
    tool_name: str | None
    command: str | None
    output_preview: str | None

    model_config = {"from_attributes": True}


class SessionChangeShapeResponse(BaseModel):
    files_touched_count: int
    named_touched_files: list[str] | None
    commit_files_changed: int
    lines_added: int
    lines_deleted: int
    diff_size: int
    edit_operations: int
    create_operations: int
    delete_operations: int
    rename_operations: int
    churn_files_count: int
    rewrite_indicator: bool
    revert_indicator: bool

    model_config = {"from_attributes": True}


class SessionRecoveryPathResponse(BaseModel):
    friction_detected: bool
    first_friction_ordinal: int | None
    recovery_step_count: int
    recovery_strategies: list[RecoveryStrategy] | None
    recovery_result: RecoveryResult
    final_outcome: str | None
    last_verification_status: ExecutionEvidenceStatus | None
    sample_recovery_commands: list[str] | None

    model_config = {"from_attributes": True}


class SessionWorkflowProfileResponse(BaseModel):
    fingerprint_id: str | None
    label: str | None
    steps: list[WorkflowStep] | None
    archetype: SessionArchetype | None
    archetype_source: ArchetypeSource | None
    archetype_reason: str | None
    top_tools: list[str] | None
    delegation_count: int
    verification_run_count: int

    model_config = {"from_attributes": True}


class SessionDelegationEdgeResponse(BaseModel):
    source_node: str
    target_node: str
    edge_type: DelegationEdgeType
    tool_name: str
    call_count: int
    prompt_preview: str | None = None

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


class SessionCustomizationPayload(BaseModel):
    customization_type: CustomizationType
    state: CustomizationState
    identifier: str
    provenance: CustomizationProvenance = "unknown"
    source_classification: CustomizationSourceClassification = "unknown"
    display_name: str | None = None
    source_path: str | None = None
    invocation_count: int = 0
    details: dict[str, Any] | None = None


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
    billing_mode: str | None = None
    first_prompt: str | None = None
    summary: str | None = None
    facets: SessionFacetsPayload | None = None
    tool_usages: list[ToolUsagePayload] | None = None
    customizations: list[SessionCustomizationPayload] | None = None
    model_usages: list[ModelUsagePayload] | None = None
    messages: list[SessionMessagePayload] | None = None
    git_remote_url: str | None = None
    commits: list[CommitPayload] | None = None

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
    agent_type: AgentType = "claude_code"
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
    has_workflow_profile: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionDetailResponse(SessionResponse):
    facets: SessionFacetsResponse | None = None
    tool_usages: list[ToolUsageResponse] = []
    customizations: list[SessionCustomizationResponse] = []
    delegation_edges: list[SessionDelegationEdgeResponse] = []
    model_usages: list[ModelUsageResponse] = []
    execution_evidence: list[SessionExecutionEvidenceResponse] = []
    change_shape: SessionChangeShapeResponse | None = None
    recovery_path: SessionRecoveryPathResponse | None = None
    workflow_profile: SessionWorkflowProfileResponse | None = None


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


class InterventionMetricsSnapshot(BaseModel):
    window_start: datetime
    window_end: datetime
    total_sessions: int
    success_rate: float | None = None
    avg_cost_per_session: float | None = None
    cost_per_successful_outcome: float | None = None
    friction_events: int = 0
    total_prs: int = 0
    findings_per_pr: float | None = None


class InterventionEngineerSummary(BaseModel):
    id: str
    name: str
    email: str


class InterventionCreate(BaseModel):
    title: str
    description: str
    category: str
    severity: str = "info"
    team_id: str | None = None
    engineer_id: str | None = None
    owner_engineer_id: str | None = None
    project_name: str | None = None
    due_date: date | None = None
    status: InterventionStatus = "planned"
    source_type: str | None = None
    source_title: str | None = None
    evidence: dict[str, Any] | None = None
    baseline_start_at: datetime | None = None
    baseline_end_at: datetime | None = None


class InterventionUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category: str | None = None
    severity: str | None = None
    team_id: str | None = None
    engineer_id: str | None = None
    owner_engineer_id: str | None = None
    project_name: str | None = None
    due_date: date | None = None
    status: InterventionStatus | None = None
    source_type: str | None = None
    source_title: str | None = None
    evidence: dict[str, Any] | None = None


class InterventionResponse(BaseModel):
    id: str
    team_id: str | None
    team_name: str | None = None
    engineer_id: str | None
    engineer: InterventionEngineerSummary | None = None
    owner_engineer_id: str | None
    owner_engineer: InterventionEngineerSummary | None = None
    created_by_engineer_id: str | None
    project_name: str | None
    category: str
    severity: str
    status: InterventionStatus
    title: str
    description: str
    due_date: date | None
    completed_at: datetime | None
    source_type: str | None
    source_title: str | None
    evidence: dict[str, Any] | None
    baseline_start_at: datetime | None
    baseline_end_at: datetime | None
    baseline_metrics: InterventionMetricsSnapshot | None = None
    current_metrics: InterventionMetricsSnapshot | None = None
    created_at: datetime
    updated_at: datetime


class InterventionEffectivenessSummary(BaseModel):
    total_interventions: int
    completed_interventions: int
    measured_interventions: int
    improved_interventions: int
    improvement_rate: float | None = None
    avg_completion_days: float | None = None
    avg_success_rate_delta: float | None = None
    avg_friction_delta: float | None = None
    avg_findings_per_pr_delta: float | None = None
    avg_cost_per_session_delta: float | None = None


class InterventionEffectivenessGroup(BaseModel):
    key: str
    label: str
    completed_interventions: int
    measured_interventions: int
    improved_interventions: int
    improvement_rate: float | None = None
    avg_completion_days: float | None = None
    avg_success_rate_delta: float | None = None
    avg_friction_delta: float | None = None
    avg_findings_per_pr_delta: float | None = None
    avg_cost_per_session_delta: float | None = None


class InterventionEffectivenessResponse(BaseModel):
    summary: InterventionEffectivenessSummary
    by_team: list[InterventionEffectivenessGroup]
    by_project: list[InterventionEffectivenessGroup]
    by_engineer_cohort: list[InterventionEffectivenessGroup]


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


class WorkflowCostBreakdown(BaseModel):
    dimension: str
    label: str
    session_count: int
    total_estimated_cost: float
    avg_cost_per_session: float | None
    cost_per_successful_outcome: float | None


class CostAnalytics(BaseModel):
    total_estimated_cost: float
    model_breakdown: list[ModelCostBreakdown]
    daily_costs: list[DailyCostEntry]
    workflow_breakdown: list[WorkflowCostBreakdown] = []


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


class CrossProjectComparisonEntry(BaseModel):
    project_name: str
    total_sessions: int
    unique_engineers: int
    effectiveness_score: float | None = None
    effectiveness_rate: float | None = None
    quality_rate: float | None = None
    friction_rate: float | None = None
    avg_cost_per_session: float | None = None
    measurement_confidence: float | None = None
    ai_readiness_score: float | None = None
    dominant_agent_type: AgentType | None = None
    top_recommendation_title: str | None = None


class CrossProjectComparisonResponse(BaseModel):
    compared_projects: int
    easiest_projects: list[CrossProjectComparisonEntry] = Field(default_factory=list)
    hardest_projects: list[CrossProjectComparisonEntry] = Field(default_factory=list)


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


class AgentSourceQuality(BaseModel):
    agent_type: AgentType
    session_count: int
    transcript_parity: TelemetryParity
    transcript_coverage_pct: float
    tool_call_parity: TelemetryParity
    tool_call_coverage_pct: float
    model_usage_parity: TelemetryParity
    model_usage_coverage_pct: float
    facet_parity: TelemetryParity
    facet_coverage_pct: float
    native_discovery_parity: TelemetryParity


class RepositoryQuality(BaseModel):
    repository_full_name: str
    session_count: int
    sessions_with_commits: int
    sessions_with_linked_pull_requests: int
    github_sync_coverage_pct: float | None = None
    has_github_id: bool
    has_default_branch: bool
    metadata_coverage_pct: float
    readiness_checked: bool


class WorkflowProfileCoverageRow(BaseModel):
    agent_type: AgentType
    session_count: int
    sessions_with_workflow_profiles: int
    workflow_profile_coverage_pct: float


class MeasurementIntegrityStats(BaseModel):
    total_sessions: int
    sessions_with_messages: int
    sessions_with_facets: int
    sessions_with_workflow_profiles: int
    facet_coverage_pct: float
    transcript_coverage_pct: float
    workflow_profile_coverage_pct: float
    sessions_with_commit_sync_target: int
    sessions_with_linked_pull_requests: int
    github_sync_coverage_pct: float
    repositories_in_scope: int
    repositories_with_complete_metadata: int
    repositories_with_readiness_check: int
    repository_metadata_coverage_pct: float
    sessions_missing_transcript_telemetry: int
    sessions_missing_tool_telemetry: int
    sessions_missing_model_telemetry: int
    low_confidence_sessions: int
    missing_confidence_sessions: int
    legacy_outcome_sessions: int
    legacy_goal_category_sessions: int
    remaining_legacy_rows: int
    source_quality: list[AgentSourceQuality] = Field(default_factory=list)
    repository_quality: list[RepositoryQuality] = Field(default_factory=list)
    workflow_profile_quality: list[WorkflowProfileCoverageRow] = Field(default_factory=list)


class FacetNormalizationSummary(BaseModel):
    rows_scanned: int
    rows_updated: int
    remaining_legacy_rows: int


class WorkflowProfileBackfillSummary(BaseModel):
    sessions_scanned: int
    profiles_created: int
    profiles_updated: int
    profiles_deleted: int
    sessions_unchanged: int
    sessions_skipped: int


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


class RootCauseCluster(BaseModel):
    cluster_id: str
    title: str
    cause_category: str
    workflow_stage: str
    session_count: int
    occurrence_count: int
    success_rate: float | None
    avg_impact_score: float | None
    top_friction_types: list[str]
    common_tools: list[str]
    transcript_cues: list[str]
    sample_details: list[str]


class RecoveryOverview(BaseModel):
    sessions_with_recovery_paths: int
    recovered_sessions: int
    abandoned_sessions: int
    unresolved_sessions: int
    recovery_rate: float | None
    avg_recovery_steps: float | None


class RecoveryPattern(BaseModel):
    strategy: RecoveryStrategy
    session_count: int
    recovered_sessions: int
    abandoned_sessions: int
    unresolved_sessions: int
    recovery_rate: float | None
    avg_recovery_steps: float | None
    sample_commands: list[str]


class BottleneckAnalytics(BaseModel):
    friction_impacts: list[FrictionImpact]
    project_friction: list[ProjectFriction]
    friction_trends: list[FrictionTrend]
    root_cause_clusters: list[RootCauseCluster]
    recovery_overview: RecoveryOverview | None = None
    recovery_patterns: list[RecoveryPattern] = []
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


class ReusableAssetAnalytics(BaseModel):
    identifier: str
    customization_type: str
    provenance: CustomizationProvenance
    source_classification: CustomizationSourceClassification
    engineer_count: int
    session_count: int
    total_invocations: int
    adoption_rate: float
    success_rate: float | None = None
    avg_session_cost: float | None = None
    cost_per_successful_outcome: float | None = None
    primary_workflow_archetype: str | None = None
    workflow_archetypes: list[str] = []
    top_projects: list[str] = []


class SkillInventoryResponse(BaseModel):
    engineer_profiles: list[EngineerSkillProfile]
    team_skill_gaps: list[TeamSkillGap]
    reusable_assets: list[ReusableAssetAnalytics] = []
    underused_reusable_assets: list[ReusableAssetAnalytics] = []
    total_engineers: int
    total_session_types: int
    total_tools_used: int


# --- Learning Paths ---


class LearningRecommendationExemplar(BaseModel):
    session_id: str
    title: str
    engineer_name: str
    project_name: str | None = None
    summary: str | None = None
    relevance_reason: str
    workflow_archetype: str | None = None
    workflow_fingerprint: str | None = None
    duration_seconds: float | None
    estimated_cost: float | None = None
    tools_used: list[str]


class LearningRecommendation(BaseModel):
    category: str  # "session_type_gap", "tool_gap", "complexity", "goal_gap"
    skill_area: str
    title: str
    description: str
    priority: str  # "high", "medium", "low"
    evidence: dict
    exemplars: list[LearningRecommendationExemplar] = []


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


class ToolRecommendation(BaseModel):
    tool_name: str
    title: str
    description: str
    priority: str
    related_skill_areas: list[str] = Field(default_factory=list)
    related_categories: list[str] = Field(default_factory=list)
    matching_projects: list[str] = Field(default_factory=list)
    supporting_exemplar_count: int = 0
    project_context_match_count: int = 0
    exemplar: LearningRecommendationExemplar | None = None


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


class BrightSpot(BaseModel):
    bright_spot_id: str
    title: str
    summary: str
    cluster_type: str
    cluster_label: str
    session_count: int
    engineer_count: int
    success_rate: float | None
    avg_duration: float | None
    exemplar_session_id: str
    exemplar_engineer_id: str
    exemplar_engineer_name: str
    exemplar_duration_seconds: float | None
    exemplar_tools: list[str]


class ExemplarPatternReference(BaseModel):
    cluster_id: str
    cluster_type: str
    cluster_label: str
    session_count: int
    engineer_count: int
    success_rate: float | None


class ExemplarSession(BaseModel):
    exemplar_id: str
    title: str
    summary: str
    why_selected: str
    session_id: str
    engineer_id: str
    engineer_name: str
    project_name: str | None = None
    outcome: str | None = None
    helpfulness: str | None = None
    session_summary: str | None = None
    duration_seconds: float | None
    estimated_cost: float | None = None
    tools_used: list[str]
    workflow_archetype: str | None = None
    workflow_fingerprint: str | None = None
    workflow_steps: list[str] = []
    supporting_session_count: int
    supporting_engineer_count: int
    supporting_pattern_count: int
    success_rate: float | None
    linked_patterns: list[ExemplarPatternReference]


class PatternSharingResponse(BaseModel):
    patterns: list[SharedPattern]
    bright_spots: list[BrightSpot] = []
    exemplar_sessions: list[ExemplarSession] = []
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


class QualityAttributionRow(BaseModel):
    dimension: str
    label: str
    linked_sessions: int
    linked_prs: int
    merge_rate: float | None
    avg_review_comments_per_pr: float | None
    avg_findings_per_pr: float | None
    high_severity_findings_per_pr: float | None
    avg_time_to_merge_hours: float | None
    findings_fix_rate: float | None


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


# --- Review Findings ---


class ReviewFindingSummary(BaseModel):
    id: str
    source: str
    severity: str
    title: str
    description: str | None
    file_path: str | None
    line_number: int | None
    status: str
    detected_at: datetime
    resolved_at: datetime | None = None
    pr_number: int | None = None
    repository: str | None = None

    model_config = {"from_attributes": True}


class FindingsOverview(BaseModel):
    total_findings: int
    by_severity: dict[str, int]
    by_source: dict[str, int]
    fix_rate: float | None
    avg_findings_per_pr: float | None
    findings_trend: list[dict] = []


class QualityMetricsResponse(BaseModel):
    overview: QualityOverview
    daily_volume: list[DailyCodeVolume]
    by_session_type: list[QualityByType]
    engineer_quality: list[EngineerQuality]
    attribution: list[QualityAttributionRow]
    recent_prs: list[PRSummary]
    findings_overview: FindingsOverview | None = None
    sessions_analyzed: int
    github_connected: bool


class EffectivenessBreakdown(BaseModel):
    success_rate: float | None = None
    cost_efficiency: float | None = None
    quality_outcomes: float | None = None
    follow_through: float | None = None


class EffectivenessScore(BaseModel):
    score: float | None = None
    breakdown: EffectivenessBreakdown = Field(default_factory=EffectivenessBreakdown)
    cost_per_successful_outcome: float | None = None
    benchmark_cost_per_successful_outcome: float | None = None


class ProjectScorecard(BaseModel):
    adoption_rate: float | None = None
    effectiveness_rate: float | None = None
    effectiveness_score: EffectivenessScore | None = None
    quality_rate: float | None = None
    avg_cost_per_session: float | None = None
    cost_per_successful_outcome: float | None = None
    measurement_confidence: float | None = None


class LanguageShare(BaseModel):
    language: str
    share_pct: float


class ProjectRepositorySummary(BaseModel):
    repository: str
    session_count: int
    default_branch: str | None = None
    readiness_checked: bool
    ai_readiness_score: float | None = None
    has_claude_md: bool | None = None
    has_agents_md: bool | None = None
    has_claude_dir: bool | None = None
    primary_language: str | None = None
    language_mix: list[LanguageShare] = Field(default_factory=list)
    repo_size_kb: int | None = None
    repo_size_bucket: str | None = None
    has_test_harness: bool | None = None
    has_ci_pipeline: bool | None = None
    test_maturity_score: float | None = None


class ProjectEnablementSummary(BaseModel):
    linked_repository_count: int = 0
    agent_type_counts: dict[str, int] = {}
    session_type_counts: dict[str, int] = {}
    permission_mode_counts: dict[str, int] = {}
    top_tools: list[str] = []
    top_models: list[str] = []
    recommendations: list[Recommendation] = Field(default_factory=list)


class ProjectRepositoryContextSummary(BaseModel):
    repositories_with_context: int = 0
    avg_repo_size_kb: float | None = None
    avg_test_maturity_score: float | None = None
    repositories_with_test_harness: int = 0
    repositories_with_ci_pipeline: int = 0
    language_mix: list[LanguageShare] = Field(default_factory=list)
    size_distribution: dict[str, int] = Field(default_factory=dict)


class ProjectAgentMixEntry(BaseModel):
    agent_type: AgentType
    session_count: int
    share_of_sessions: float
    unique_engineers: int
    success_rate: float | None = None
    friction_rate: float | None = None
    avg_health_score: float | None = None
    avg_cost_per_session: float | None = None
    top_tools: list[str] = Field(default_factory=list)
    top_models: list[str] = Field(default_factory=list)


class ProjectAgentMixSummary(BaseModel):
    total_sessions: int
    compared_agents: int
    dominant_agent_type: AgentType | None = None
    entries: list[ProjectAgentMixEntry] = Field(default_factory=list)


class ProjectWorkflowFingerprint(BaseModel):
    fingerprint_id: str
    label: str
    session_type: str | None = None
    steps: list[str] = Field(default_factory=list)
    session_count: int
    share_of_sessions: float
    success_rate: float | None = None
    avg_duration_seconds: float | None = None
    top_tools: list[str] = Field(default_factory=list)
    top_friction_types: list[str] = Field(default_factory=list)


class ProjectFrictionHotspot(BaseModel):
    friction_type: str
    session_count: int
    share_of_sessions: float
    total_occurrences: int
    impact_score: float | None = None
    linked_fingerprints: list[str] = Field(default_factory=list)
    sample_details: list[str] = Field(default_factory=list)


class ProjectWorkflowSummary(BaseModel):
    fingerprinted_sessions: int
    total_sessions: int
    coverage_pct: float
    fingerprints: list[ProjectWorkflowFingerprint] = Field(default_factory=list)
    friction_hotspots: list[ProjectFrictionHotspot] = Field(default_factory=list)


class ProjectWorkspaceResponse(BaseModel):
    project: ProjectStats
    scorecard: ProjectScorecard
    overview: OverviewStats
    productivity: ProductivityMetrics
    cost: CostAnalytics
    quality: QualityMetricsResponse
    friction: ProjectFriction | None = None
    friction_impacts: list[FrictionImpact] = []
    repositories: list[ProjectRepositorySummary] = []
    enablement: ProjectEnablementSummary
    agent_mix: ProjectAgentMixSummary
    repository_context: ProjectRepositoryContextSummary
    workflow_summary: ProjectWorkflowSummary


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


class WorkflowPlaybook(BaseModel):
    playbook_id: str
    title: str
    summary: str
    scope: str
    adoption_state: str
    session_type: str | None = None
    steps: list[str] = Field(default_factory=list)
    recommended_tools: list[str] = Field(default_factory=list)
    caution_friction_types: list[str] = Field(default_factory=list)
    example_projects: list[str] = Field(default_factory=list)
    supporting_session_count: int
    supporting_peer_count: int
    success_rate: float | None = None
    friction_free_rate: float | None = None
    avg_duration_seconds: float | None = None
    engineer_usage_count: int = 0


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
    tool_recommendations: list[ToolRecommendation] = []
    quality: dict  # flexible dict for quality metrics
    leverage_score: float | None = None
    effectiveness: EffectivenessScore | None = None
    projects: list[str] = []
    tool_rankings: list[ToolRanking] = []
    workflow_playbooks: list[WorkflowPlaybook] = []


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


class LeverageBreakdown(BaseModel):
    tool_diversity: float = 0.0
    category_spread: float = 0.0
    tool_mastery: float = 0.0
    orch_skill_ratio: float = 0.0
    agent_team_score: float = 0.0
    orchestration_depth: float = 0.0
    cache_efficiency: float = 0.0
    model_diversity: float = 0.0
    efficiency: float = 0.0


class EngineerLeverageProfile(BaseModel):
    engineer_id: str
    name: str
    leverage_score: float
    effectiveness_score: float | None = None
    leverage_breakdown: LeverageBreakdown | None = None
    total_tool_calls: int
    orchestration_calls: int
    skill_calls: int
    mcp_calls: int
    model_count: int = 0
    cost_tier_count: int = 0
    uses_agent_teams: bool = False
    top_agents: list[str]
    top_skills: list[str]
    top_models: list[str] = []
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


class CustomizationUsage(BaseModel):
    identifier: str
    customization_type: str
    provenance: CustomizationProvenance
    source_classification: CustomizationSourceClassification = "unknown"
    total_invocations: int
    session_count: int
    engineer_count: int
    project_count: int
    top_projects: list[str] = []
    top_engineers: list[str] = []


class StackCustomization(BaseModel):
    identifier: str
    customization_type: str
    provenance: CustomizationProvenance
    source_classification: CustomizationSourceClassification = "unknown"
    invocation_count: int


class HighPerformerStack(BaseModel):
    stack_id: str
    label: str
    customizations: list[StackCustomization]
    engineer_count: int
    session_count: int
    avg_effectiveness_score: float | None = None
    avg_leverage_score: float
    top_projects: list[str] = []
    top_engineers: list[str] = []


class TeamCustomizationLandscape(BaseModel):
    team_id: str
    team_name: str
    engineer_count: int
    engineers_using_explicit_customizations: int
    explicit_customization_count: int
    adoption_rate: float
    avg_effectiveness_score: float | None = None
    top_customizations: list[str] = []
    unique_customizations: list[str] = []


class CustomizationStateFunnel(BaseModel):
    identifier: str
    customization_type: str
    provenance: CustomizationProvenance
    source_classification: CustomizationSourceClassification
    available_session_count: int
    enabled_session_count: int
    invoked_session_count: int
    available_engineer_count: int
    enabled_engineer_count: int
    invoked_engineer_count: int
    activation_rate: float | None = None
    usage_rate: float | None = None
    available_not_enabled_engineer_count: int = 0
    enabled_not_invoked_engineer_count: int = 0


class ToolchainReliabilityEntry(BaseModel):
    identifier: str
    surface_type: str
    provenance: CustomizationProvenance | None = None
    source_classification: CustomizationSourceClassification | None = None
    session_count: int
    engineer_count: int
    friction_session_count: int
    friction_session_rate: float | None = None
    failure_session_count: int
    failure_session_rate: float | None = None
    recovery_rate: float | None = None
    success_rate: float | None = None
    abandonment_rate: float | None = None
    avg_recovery_steps: float | None = None
    top_friction_types: list[str] = []


class DelegationPatternSummary(BaseModel):
    target_node: str
    edge_type: DelegationEdgeType
    session_count: int
    engineer_count: int
    total_calls: int
    success_rate: float | None = None
    top_workflow_archetypes: list[str] = []


class CustomizationOutcomeAttribution(BaseModel):
    dimension: str
    label: str
    customization_type: str | None = None
    provenance: CustomizationProvenance | None = None
    source_classification: CustomizationSourceClassification | None = None
    support_engineer_count: int
    support_session_count: int
    avg_effectiveness_score: float | None = None
    avg_leverage_score: float
    avg_success_rate: float | None = None
    avg_cost_per_successful_outcome: float | None = None
    avg_pr_merge_rate: float | None = None
    cohort_share: float | None = None


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
    customization_breakdown: list[CustomizationUsage] = []
    high_performer_stacks: list[HighPerformerStack] = []
    team_customization_landscape: list[TeamCustomizationLandscape] = []
    customization_state_funnel: list[CustomizationStateFunnel] = []
    toolchain_reliability: list[ToolchainReliabilityEntry] = []
    delegation_patterns: list[DelegationPatternSummary] = []
    customization_outcomes: list[CustomizationOutcomeAttribution] = []
    project_readiness: list[ProjectReadinessEntry]
    sessions_analyzed: int
    avg_leverage_score: float
    avg_effectiveness_score: float | None = None
    orchestration_adoption_rate: float
    team_orchestration_adoption_rate: float = 0.0
    explicit_customization_adoption_rate: float = 0.0
    model_diversity_avg: float = 0.0


# --- Coaching Brief ---


class CoachingSection(BaseModel):
    title: str
    items: list[str]


class CoachingBrief(BaseModel):
    status_summary: str
    sections: list[CoachingSection]
    sessions_analyzed: int = 0
    generated_at: str


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


# --- FinOps: Cache Analytics ---


class ModelCacheBreakdown(BaseModel):
    model_name: str
    cache_read_tokens: int
    cache_creation_tokens: int
    input_tokens: int
    cache_hit_rate: float | None
    estimated_savings: float


class EngineerCacheEfficiency(BaseModel):
    engineer_id: str
    engineer_name: str
    cache_hit_rate: float | None
    estimated_savings: float
    potential_additional_savings: float
    total_cache_read_tokens: int
    total_input_tokens: int


class CacheAnalyticsResponse(BaseModel):
    total_cache_read_tokens: int
    total_cache_creation_tokens: int
    total_input_tokens: int
    cache_hit_rate: float | None
    cache_savings_estimate: float | None
    daily_cache_trend: list[DailyCacheEntry] = []
    model_cache_breakdown: list[ModelCacheBreakdown] = []
    engineer_cache_breakdown: list[EngineerCacheEfficiency] = []
    total_potential_additional_savings: float = 0.0


# --- FinOps: Cost Modeling ---


class PlanTier(BaseModel):
    name: str  # "api_key", "pro", "max_5x", "max_20x"
    label: str
    monthly_cost: float


class EngineerCostComparison(BaseModel):
    engineer_id: str
    engineer_name: str
    monthly_api_cost: float
    recommended_plan: str  # tier name
    recommended_plan_cost: float
    savings_vs_api: float  # positive = subscription saves money
    current_billing_mode: str | None
    daily_avg_cost: float


class PlanAllocationSummary(BaseModel):
    plan: str  # tier name
    label: str
    monthly_cost_per_seat: float
    engineer_count: int
    total_monthly_cost: float


class CostModelingResponse(BaseModel):
    period_days: int
    plan_tiers: list[PlanTier]
    engineers: list[EngineerCostComparison]
    allocation: list[PlanAllocationSummary]
    total_api_cost_monthly: float
    total_optimal_cost_monthly: float
    total_savings_monthly: float


# --- FinOps: Forecasting ---


class ForecastPoint(BaseModel):
    date: str
    projected_cost: float
    upper_bound: float
    lower_bound: float


class CostForecastResponse(BaseModel):
    historical: list[DailyCostEntry] = []
    forecast: list[ForecastPoint] = []
    monthly_projection: float
    trend_direction: str


# --- FinOps: Budgets ---


class BudgetCreate(BaseModel):
    team_id: str | None = None
    name: str
    amount: float
    period: str = "monthly"
    alert_threshold_pct: int = 80


class BudgetUpdate(BaseModel):
    name: str | None = None
    amount: float | None = None
    period: str | None = None
    alert_threshold_pct: int | None = None


class BudgetStatus(BaseModel):
    id: str
    name: str
    team_id: str | None
    team_name: str | None = None
    amount: float
    period: str
    current_spend: float
    burn_rate_daily: float
    projected_end_of_period: float
    alert_threshold_pct: int
    pct_used: float
    status: str  # "on_track" | "warning" | "over_budget"

    model_config = {"from_attributes": True}
