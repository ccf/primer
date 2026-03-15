import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from primer.common.database import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    engineers: Mapped[list["Engineer"]] = relationship(back_populates="team")


class Engineer(Base):
    __tablename__ = "engineers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    team_id: Mapped[str | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    role: Mapped[str] = mapped_column(String(20), nullable=False, server_default="engineer")
    github_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    github_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    is_active: Mapped[bool] = mapped_column(Boolean, server_default="1", nullable=False)

    team: Mapped[Team | None] = relationship(back_populates="engineers")
    sessions: Mapped[list["Session"]] = relationship(back_populates="engineer")
    daily_stats: Mapped[list["DailyStats"]] = relationship(back_populates="engineer")
    ingest_events: Mapped[list["IngestEvent"]] = relationship(back_populates="engineer")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="engineer")


class GitRepository(Base):
    __tablename__ = "git_repositories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name: Mapped[str] = mapped_column(String(255), unique=True)
    github_id: Mapped[int | None] = mapped_column(Integer, unique=True)
    default_branch: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    has_claude_md: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    has_agents_md: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    has_claude_dir: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ai_readiness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_readiness_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    primary_language: Mapped[str | None] = mapped_column(String(100), nullable=True)
    language_breakdown: Mapped[dict[str, int] | None] = mapped_column(JSON, nullable=True)
    repo_size_kb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    has_test_harness: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    has_ci_pipeline: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    test_maturity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    repo_context_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    sessions: Mapped[list["Session"]] = relationship(back_populates="repository")
    pull_requests: Mapped[list["PullRequest"]] = relationship(back_populates="repository")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    engineer_id: Mapped[str] = mapped_column(ForeignKey("engineers.id"), nullable=False)
    repository_id: Mapped[str | None] = mapped_column(
        ForeignKey("git_repositories.id"), nullable=True
    )
    agent_type: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="claude_code"
    )
    project_path: Mapped[str | None] = mapped_column(String(1024))
    project_name: Mapped[str | None] = mapped_column(String(255))
    git_branch: Mapped[str | None] = mapped_column(String(255))
    agent_version: Mapped[str | None] = mapped_column(String(50))
    permission_mode: Mapped[str | None] = mapped_column(String(50))
    end_reason: Mapped[str | None] = mapped_column(String(100))
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    user_message_count: Mapped[int] = mapped_column(Integer, default=0)
    assistant_message_count: Mapped[int] = mapped_column(Integer, default=0)
    tool_call_count: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_creation_tokens: Mapped[int] = mapped_column(Integer, default=0)
    primary_model: Mapped[str | None] = mapped_column(String(100))
    billing_mode: Mapped[str | None] = mapped_column(String(30), nullable=True)
    first_prompt: Mapped[str | None] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(Text)
    has_facets: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    engineer: Mapped[Engineer] = relationship(back_populates="sessions")
    repository: Mapped[GitRepository | None] = relationship(back_populates="sessions")
    facets: Mapped["SessionFacets | None"] = relationship(
        back_populates="session", uselist=False, cascade="all, delete-orphan"
    )
    tool_usages: Mapped[list["ToolUsage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    model_usages: Mapped[list["ModelUsage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    messages: Mapped[list["SessionMessage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    execution_evidence: Mapped[list["SessionExecutionEvidence"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    change_shape: Mapped["SessionChangeShape | None"] = relationship(
        back_populates="session", uselist=False, cascade="all, delete-orphan"
    )
    recovery_path: Mapped["SessionRecoveryPath | None"] = relationship(
        back_populates="session", uselist=False, cascade="all, delete-orphan"
    )
    workflow_profile: Mapped["SessionWorkflowProfile | None"] = relationship(
        back_populates="session", uselist=False, cascade="all, delete-orphan"
    )
    commits: Mapped[list["SessionCommit"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )

    @property
    def has_workflow_profile(self) -> bool:
        return self.workflow_profile is not None


class SessionFacets(Base):
    __tablename__ = "session_facets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False, unique=True)
    underlying_goal: Mapped[str | None] = mapped_column(Text)
    goal_categories: Mapped[list[str] | None] = mapped_column(JSON)
    outcome: Mapped[str | None] = mapped_column(String(50))
    confidence_score: Mapped[float | None] = mapped_column(Float)
    session_type: Mapped[str | None] = mapped_column(String(50))
    primary_success: Mapped[str | None] = mapped_column(String(50))
    agent_helpfulness: Mapped[str | None] = mapped_column(String(50))
    brief_summary: Mapped[str | None] = mapped_column(Text)
    user_satisfaction_counts: Mapped[dict | None] = mapped_column(JSON)
    friction_counts: Mapped[dict | None] = mapped_column(JSON)
    friction_detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped[Session] = relationship(back_populates="facets")


class ToolUsage(Base):
    __tablename__ = "tool_usages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(255), nullable=False)
    call_count: Mapped[int] = mapped_column(Integer, default=0)

    session: Mapped[Session] = relationship(back_populates="tool_usages")


class ModelUsage(Base):
    __tablename__ = "model_usages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_creation_tokens: Mapped[int] = mapped_column(Integer, default=0)

    session: Mapped[Session] = relationship(back_populates="model_usages")


class DailyStats(Base):
    __tablename__ = "daily_stats"
    __table_args__ = (
        UniqueConstraint("engineer_id", "date", "agent_type", name="uq_daily_stats_engineer_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    engineer_id: Mapped[str] = mapped_column(ForeignKey("engineers.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    agent_type: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="claude_code"
    )
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    session_count: Mapped[int] = mapped_column(Integer, default=0)
    tool_call_count: Mapped[int] = mapped_column(Integer, default=0)

    engineer: Mapped[Engineer] = relationship(back_populates="daily_stats")


class IngestEvent(Base):
    __tablename__ = "ingest_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    engineer_id: Mapped[str] = mapped_column(ForeignKey("engineers.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(36))
    payload_size_bytes: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    engineer: Mapped[Engineer] = relationship(back_populates="ingest_events")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    engineer_id: Mapped[str] = mapped_column(ForeignKey("engineers.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    engineer: Mapped[Engineer] = relationship(back_populates="refresh_tokens")


class AlertConfig(Base):
    __tablename__ = "alert_configs"
    __table_args__ = (
        UniqueConstraint("team_id", "alert_type", name="uq_alert_config_team_type"),
        Index(
            "uq_alert_config_global_type",
            "alert_type",
            unique=True,
            sqlite_where=text("team_id IS NULL"),
            postgresql_where=text("team_id IS NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    team_id: Mapped[str | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    actor_role: Mapped[str] = mapped_column(String(20), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SessionMessage(Base):
    __tablename__ = "session_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content_text: Mapped[str | None] = mapped_column(Text)
    tool_calls: Mapped[list | None] = mapped_column(JSON)
    tool_results: Mapped[list | None] = mapped_column(JSON)
    token_count: Mapped[int | None] = mapped_column(Integer)
    model: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped[Session] = relationship(back_populates="messages")


class SessionExecutionEvidence(Base):
    __tablename__ = "session_execution_evidence"
    __table_args__ = (
        Index(
            "ix_session_execution_evidence_session_ordinal",
            "session_id",
            "ordinal",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    evidence_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    tool_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    command: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped[Session] = relationship(back_populates="execution_evidence")


class SessionChangeShape(Base):
    __tablename__ = "session_change_shapes"
    __table_args__ = (
        Index(
            "ix_session_change_shapes_session_id",
            "session_id",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    files_touched_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    named_touched_files: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    commit_files_changed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lines_added: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lines_deleted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    diff_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    edit_operations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    create_operations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delete_operations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rename_operations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    churn_files_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rewrite_indicator: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    revert_indicator: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped[Session] = relationship(back_populates="change_shape")


class SessionRecoveryPath(Base):
    __tablename__ = "session_recovery_paths"
    __table_args__ = (
        Index(
            "ix_session_recovery_paths_session_id",
            "session_id",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    friction_detected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    first_friction_ordinal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recovery_step_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recovery_strategies: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    recovery_result: Mapped[str] = mapped_column(String(20), nullable=False, default="unresolved")
    final_outcome: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_verification_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sample_recovery_commands: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped[Session] = relationship(back_populates="recovery_path")


class SessionWorkflowProfile(Base):
    __tablename__ = "session_workflow_profiles"
    __table_args__ = (
        Index(
            "ix_session_workflow_profiles_session_id",
            "session_id",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    fingerprint_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    steps: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    archetype: Mapped[str | None] = mapped_column(String(50), nullable=True)
    archetype_source: Mapped[str | None] = mapped_column(String(20), nullable=True)
    archetype_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    top_tools: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    delegation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    verification_run_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped[Session] = relationship(back_populates="workflow_profile")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    team_id: Mapped[str | None] = mapped_column(ForeignKey("teams.id"))
    engineer_id: Mapped[str | None] = mapped_column(ForeignKey("engineers.id"))
    alert_type: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    metric_name: Mapped[str] = mapped_column(String(100))
    expected_value: Mapped[float | None] = mapped_column(Float)
    actual_value: Mapped[float | None] = mapped_column(Float)
    threshold: Mapped[float | None] = mapped_column(Float)
    detected_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime)
    dismissed: Mapped[bool] = mapped_column(Boolean, default=False)


class PullRequest(Base):
    __tablename__ = "pull_requests"
    __table_args__ = (UniqueConstraint("repository_id", "github_pr_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id: Mapped[str] = mapped_column(ForeignKey("git_repositories.id"), nullable=False)
    engineer_id: Mapped[str | None] = mapped_column(ForeignKey("engineers.id"), nullable=True)
    github_pr_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(500))
    state: Mapped[str] = mapped_column(String(20))
    head_branch: Mapped[str | None] = mapped_column(String(255))
    additions: Mapped[int] = mapped_column(Integer, default=0)
    deletions: Mapped[int] = mapped_column(Integer, default=0)
    changed_files: Mapped[int] = mapped_column(Integer, default=0)
    review_comments_count: Mapped[int] = mapped_column(Integer, default=0)
    commits_count: Mapped[int] = mapped_column(Integer, default=0)
    merged_at: Mapped[datetime | None] = mapped_column(DateTime)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)
    pr_created_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    repository: Mapped[GitRepository] = relationship(back_populates="pull_requests")
    commits: Mapped[list["SessionCommit"]] = relationship(back_populates="pull_request")
    findings: Mapped[list["ReviewFinding"]] = relationship(back_populates="pull_request")


class NarrativeCache(Base):
    __tablename__ = "narrative_cache"
    __table_args__ = (
        UniqueConstraint("scope", "scope_id", "date_range_key", name="uq_narrative_scope"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scope: Mapped[str] = mapped_column(String(20))
    scope_id: Mapped[str | None] = mapped_column(String(36))
    date_range_key: Mapped[str] = mapped_column(String(50))
    sections: Mapped[list] = mapped_column(JSON)
    model_used: Mapped[str] = mapped_column(String(100))
    data_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime)


class SessionCommit(Base):
    __tablename__ = "session_commits"
    __table_args__ = (UniqueConstraint("session_id", "commit_sha"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    repository_id: Mapped[str | None] = mapped_column(
        ForeignKey("git_repositories.id"), nullable=True
    )
    pull_request_id: Mapped[str | None] = mapped_column(
        ForeignKey("pull_requests.id"), nullable=True
    )
    commit_sha: Mapped[str] = mapped_column(String(40), nullable=False)
    commit_message: Mapped[str | None] = mapped_column(Text)
    author_name: Mapped[str | None] = mapped_column(String(255))
    author_email: Mapped[str | None] = mapped_column(String(255))
    committed_at: Mapped[datetime | None] = mapped_column(DateTime)
    files_changed: Mapped[int] = mapped_column(Integer, default=0)
    lines_added: Mapped[int] = mapped_column(Integer, default=0)
    lines_deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped["Session"] = relationship(back_populates="commits")
    pull_request: Mapped[PullRequest | None] = relationship(back_populates="commits")


class ReviewFinding(Base):
    __tablename__ = "review_findings"
    __table_args__ = (UniqueConstraint("pull_request_id", "source", "external_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pull_request_id: Mapped[str] = mapped_column(ForeignKey("pull_requests.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="open")
    detected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    pull_request: Mapped[PullRequest] = relationship(back_populates="findings")


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    team_id: Mapped[str | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False)  # "monthly" | "quarterly"
    alert_threshold_pct: Mapped[int] = mapped_column(Integer, default=80)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Intervention(Base):
    __tablename__ = "interventions"
    __table_args__ = (
        Index("ix_interventions_team_status", "team_id", "status"),
        Index("ix_interventions_engineer_status", "engineer_id", "status"),
        Index("ix_interventions_owner_status", "owner_engineer_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    team_id: Mapped[str | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    engineer_id: Mapped[str | None] = mapped_column(ForeignKey("engineers.id"), nullable=True)
    owner_engineer_id: Mapped[str | None] = mapped_column(ForeignKey("engineers.id"), nullable=True)
    created_by_engineer_id: Mapped[str | None] = mapped_column(
        ForeignKey("engineers.id"), nullable=True
    )
    project_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, server_default="info")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="planned")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    baseline_start_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    baseline_end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    baseline_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
