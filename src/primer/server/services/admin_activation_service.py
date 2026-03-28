from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from primer.common.config import settings
from primer.common.models import (
    AlertConfig,
    Budget,
    GitRepository,
    IngestEvent,
    NarrativeCache,
    PullRequest,
)
from primer.common.schemas import ActivationHubItem, ActivationHubResponse
from primer.server.services.github_service import is_configured
from primer.server.services.measurement_integrity_service import get_measurement_integrity_stats

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def get_activation_hub(db: Session) -> ActivationHubResponse:
    now = datetime.now(tz=UTC)
    integrity = get_measurement_integrity_stats(db)

    latest_ingest = db.query(IngestEvent.created_at).order_by(IngestEvent.created_at.desc()).first()
    repos_count = db.query(GitRepository).count()
    prs_count = db.query(PullRequest).count()
    budgets_count = db.query(Budget).count()
    alert_configs_count = db.query(AlertConfig).count()
    narrative_count = db.query(NarrativeCache).count()

    items = [
        _github_item(repos_count=repos_count, prs_count=prs_count),
        _budgets_item(budgets_count=budgets_count),
        _alerts_item(alert_configs_count=alert_configs_count),
        _narratives_item(narrative_count=narrative_count),
        _freshness_item(latest_ingest_at=latest_ingest[0] if latest_ingest else None, now=now),
        _coverage_item(integrity),
    ]

    ready_count = sum(1 for item in items if item.status == "ready")
    total_items = len(items)
    return ActivationHubResponse(
        ready_count=ready_count,
        total_items=total_items,
        progress_pct=round((ready_count / total_items) * 100, 1) if total_items else 0.0,
        items=items,
    )


def _github_item(*, repos_count: int, prs_count: int) -> ActivationHubItem:
    if not is_configured():
        return ActivationHubItem(
            key="github",
            title="GitHub",
            status="action_needed",
            summary="GitHub App settings are not configured yet.",
            next_action="Configure the GitHub App env vars and run a repository sync.",
        )
    if repos_count == 0:
        return ActivationHubItem(
            key="github",
            title="GitHub",
            status="attention",
            summary="GitHub is configured, but no repositories have been linked yet.",
            next_action="Sync repositories so Primer can populate PR and review quality data.",
        )
    if prs_count == 0:
        return ActivationHubItem(
            key="github",
            title="GitHub",
            status="attention",
            summary=(
                f"{repos_count} repositories linked, but no pull requests have been synced yet."
            ),
            next_action="Run the GitHub sync and confirm repository permissions.",
        )
    return ActivationHubItem(
        key="github",
        title="GitHub",
        status="ready",
        summary=f"{repos_count} repositories linked and {prs_count} pull requests synced.",
    )


def _budgets_item(*, budgets_count: int) -> ActivationHubItem:
    if budgets_count == 0:
        return ActivationHubItem(
            key="budgets",
            title="Budgets",
            status="action_needed",
            summary="No budgets are configured yet.",
            next_action="Create a budget in FinOps so burn-rate alerts and projections can work.",
        )
    return ActivationHubItem(
        key="budgets",
        title="Budgets",
        status="ready",
        summary=f"{budgets_count} budget{'s' if budgets_count != 1 else ''} configured.",
    )


def _alerts_item(*, alert_configs_count: int) -> ActivationHubItem:
    if settings.slack_alerts_enabled and settings.slack_webhook_url:
        return ActivationHubItem(
            key="alerts",
            title="Alerts",
            status="ready",
            summary=(
                f"Slack notifications enabled with {alert_configs_count} custom alert "
                f"threshold{'s' if alert_configs_count != 1 else ''}."
            ),
        )
    if alert_configs_count > 0:
        return ActivationHubItem(
            key="alerts",
            title="Alerts",
            status="attention",
            summary="Alert thresholds exist, but Slack notifications are not fully enabled.",
            next_action="Enable Slack notifications or test the webhook so alerts reach the team.",
        )
    return ActivationHubItem(
        key="alerts",
        title="Alerts",
        status="action_needed",
        summary="Alerts are using defaults and Slack notifications are not configured.",
        next_action="Review alert thresholds and enable Slack notifications.",
    )


def _narratives_item(*, narrative_count: int) -> ActivationHubItem:
    if not settings.anthropic_api_key:
        return ActivationHubItem(
            key="narratives",
            title="Narratives",
            status="action_needed",
            summary="Narrative generation is not configured.",
            next_action="Set PRIMER_ANTHROPIC_API_KEY to enable cached narrative reports.",
        )
    if narrative_count == 0:
        return ActivationHubItem(
            key="narratives",
            title="Narratives",
            status="attention",
            summary="Narratives are configured, but no cached reports have been generated yet.",
            next_action="Open a narrative surface or refresh narratives to prime the cache.",
        )
    return ActivationHubItem(
        key="narratives",
        title="Narratives",
        status="ready",
        summary=(
            f"{narrative_count} cached narrative report"
            f"{'s' if narrative_count != 1 else ''} available."
        ),
    )


def _freshness_item(*, latest_ingest_at: datetime | None, now: datetime) -> ActivationHubItem:
    if latest_ingest_at is None:
        return ActivationHubItem(
            key="freshness",
            title="Data Freshness",
            status="action_needed",
            summary="No ingest activity has been recorded yet.",
            next_action="Run primer sync or connect a hook/watcher so session data starts flowing.",
        )

    latest = latest_ingest_at if latest_ingest_at.tzinfo else latest_ingest_at.replace(tzinfo=UTC)
    age_hours = (now - latest).total_seconds() / 3600

    if age_hours <= 24:
        return ActivationHubItem(
            key="freshness",
            title="Data Freshness",
            status="ready",
            summary=f"Latest ingest activity was {round(age_hours, 1)} hours ago.",
        )
    if age_hours <= 72:
        return ActivationHubItem(
            key="freshness",
            title="Data Freshness",
            status="attention",
            summary=f"Latest ingest activity was {round(age_hours, 1)} hours ago.",
            next_action="Check sync jobs or local hooks before the data goes stale.",
        )
    return ActivationHubItem(
        key="freshness",
        title="Data Freshness",
        status="action_needed",
        summary=f"Latest ingest activity was {round(age_hours, 1)} hours ago.",
        next_action="Investigate sync failures or restart local ingestion immediately.",
    )


def _coverage_item(integrity) -> ActivationHubItem:
    total_sessions = int(integrity["total_sessions"])
    if total_sessions == 0:
        return ActivationHubItem(
            key="coverage",
            title="Measurement Coverage",
            status="action_needed",
            summary="No sessions captured yet, so coverage and quality signals are still empty.",
            next_action="Ingest sessions first, then backfill facets and workflow profiles.",
        )

    transcript = float(integrity["transcript_coverage_pct"])
    facets = float(integrity["facet_coverage_pct"])
    workflows = float(integrity["workflow_profile_coverage_pct"])
    github_sync = float(integrity["github_sync_coverage_pct"])
    summary = (
        f"Transcript {transcript:.1f}% · "
        f"Facets {facets:.1f}% · "
        f"Workflows {workflows:.1f}% · "
        f"GitHub sync {github_sync:.1f}%"
    )

    if transcript >= 80 and facets >= 80 and workflows >= 80:
        return ActivationHubItem(
            key="coverage",
            title="Measurement Coverage",
            status="ready",
            summary=summary,
        )

    return ActivationHubItem(
        key="coverage",
        title="Measurement Coverage",
        status="attention",
        summary=summary,
        next_action="Review measurement integrity and run the missing backfills.",
    )
