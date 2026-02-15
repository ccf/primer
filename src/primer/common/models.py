import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
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


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    engineer_id: Mapped[str] = mapped_column(ForeignKey("engineers.id"), nullable=False)
    project_path: Mapped[str | None] = mapped_column(String(1024))
    project_name: Mapped[str | None] = mapped_column(String(255))
    git_branch: Mapped[str | None] = mapped_column(String(255))
    claude_version: Mapped[str | None] = mapped_column(String(50))
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
    first_prompt: Mapped[str | None] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(Text)
    has_facets: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    engineer: Mapped[Engineer] = relationship(back_populates="sessions")
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


class SessionFacets(Base):
    __tablename__ = "session_facets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False, unique=True)
    underlying_goal: Mapped[str | None] = mapped_column(Text)
    goal_categories: Mapped[dict | None] = mapped_column(JSON)
    outcome: Mapped[str | None] = mapped_column(String(50))
    session_type: Mapped[str | None] = mapped_column(String(50))
    primary_success: Mapped[str | None] = mapped_column(String(50))
    claude_helpfulness: Mapped[str | None] = mapped_column(String(50))
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
    __table_args__ = (UniqueConstraint("engineer_id", "date", name="uq_daily_stats_engineer_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    engineer_id: Mapped[str] = mapped_column(ForeignKey("engineers.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
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
    __table_args__ = (UniqueConstraint("team_id", "alert_type", name="uq_alert_config_team_type"),)

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
