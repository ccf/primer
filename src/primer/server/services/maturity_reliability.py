"""Toolchain reliability helpers for maturity analytics."""

from collections import Counter
from typing import Any

from primer.common.facet_taxonomy import is_success_outcome
from primer.common.schemas import ToolchainReliabilityEntry

DEFAULT_COMPOUND_RELIABILITY_CHAIN_LENGTH = 10


def ensure_reliability_bucket(
    reliability_data: dict[tuple[str, str, str | None, str | None], dict[str, Any]],
    *,
    surface_type: str,
    identifier: str,
    provenance: str | None,
    source_classification: str | None,
) -> dict[str, Any]:
    """Return the aggregate bucket for one tool/customization surface."""
    return reliability_data.setdefault(
        (surface_type, identifier, provenance, source_classification),
        {
            "identifier": identifier,
            "surface_type": surface_type,
            "provenance": provenance,
            "source_classification": source_classification,
            "sessions": set(),
            "engineers": set(),
            "friction_sessions": set(),
            "failure_sessions": set(),
            "recovered_sessions": set(),
            "abandoned_sessions": set(),
            "recovery_steps": [],
            "success_sessions": set(),
            "friction_type_counts": Counter(),
            "total_call_count": 0,
        },
    )


def apply_session_reliability_metrics(
    bucket: dict[str, Any],
    session_id: str,
    session_metric: dict[str, object] | None,
) -> None:
    """Fold per-session friction, recovery, and outcome signals into a bucket."""
    if session_metric is None:
        return
    if session_metric["has_friction"]:
        bucket["friction_sessions"].add(session_id)
        bucket["friction_type_counts"].update(session_metric["friction_counts"])
    if session_metric["has_failure"]:
        bucket["failure_sessions"].add(session_id)
    outcome = session_metric["outcome"]
    if outcome and is_success_outcome(outcome):
        bucket["success_sessions"].add(session_id)
    if session_metric["recovery_result"] == "recovered":
        bucket["recovered_sessions"].add(session_id)
    if session_metric["recovery_result"] == "abandoned":
        bucket["abandoned_sessions"].add(session_id)
    recovery_steps = session_metric["recovery_step_count"]
    if isinstance(recovery_steps, int) and recovery_steps > 0:
        bucket["recovery_steps"].append(recovery_steps)


def build_toolchain_reliability(
    reliability_data: dict[tuple[str, str, str | None, str | None], dict[str, Any]],
    *,
    compound_reliability_chain_length: int = DEFAULT_COMPOUND_RELIABILITY_CHAIN_LENGTH,
) -> list[ToolchainReliabilityEntry]:
    """Convert reliability buckets into sorted API response rows."""
    return [
        ToolchainReliabilityEntry(
            identifier=bucket["identifier"],
            surface_type=bucket["surface_type"],
            provenance=bucket["provenance"],
            source_classification=bucket["source_classification"],
            session_count=len(bucket["sessions"]),
            engineer_count=len(bucket["engineers"]),
            total_call_count=bucket["total_call_count"],
            avg_calls_per_session=(
                round(bucket["total_call_count"] / len(bucket["sessions"]), 1)
                if bucket["sessions"]
                else 0.0
            ),
            friction_session_count=len(bucket["friction_sessions"]),
            friction_session_rate=(
                round(len(bucket["friction_sessions"]) / len(bucket["sessions"]), 3)
                if bucket["sessions"]
                else None
            ),
            failure_session_count=len(bucket["failure_sessions"]),
            failure_session_rate=(
                round(len(bucket["failure_sessions"]) / len(bucket["sessions"]), 3)
                if bucket["sessions"]
                else None
            ),
            recovery_rate=(
                round(
                    len(bucket["recovered_sessions"]) / len(bucket["friction_sessions"]),
                    3,
                )
                if bucket["friction_sessions"]
                else None
            ),
            success_rate=(
                round(len(bucket["success_sessions"]) / len(bucket["sessions"]), 3)
                if bucket["sessions"]
                else None
            ),
            compound_reliability_rate=_compound_reliability_rate(
                bucket,
                compound_reliability_chain_length,
            ),
            abandonment_rate=(
                round(len(bucket["abandoned_sessions"]) / len(bucket["sessions"]), 3)
                if bucket["sessions"]
                else None
            ),
            avg_recovery_steps=(
                round(sum(bucket["recovery_steps"]) / len(bucket["recovery_steps"]), 1)
                if bucket["recovery_steps"]
                else None
            ),
            top_friction_types=[
                friction_type
                for friction_type, _count in bucket["friction_type_counts"].most_common(3)
            ],
        )
        for bucket in sorted(
            reliability_data.values(),
            key=lambda item: (
                -len(item["failure_sessions"]),
                -len(item["friction_sessions"]),
                -len(item["sessions"]),
                item["identifier"],
            ),
        )
    ]


def _compound_reliability_rate(bucket: dict[str, Any], chain_length: int) -> float | None:
    if not bucket["sessions"]:
        return None
    success_rate = len(bucket["success_sessions"]) / len(bucket["sessions"])
    avg_calls = bucket["total_call_count"] / len(bucket["sessions"])
    if avg_calls <= 0:
        return None
    per_call_rate = success_rate ** (1.0 / avg_calls)
    return round(per_call_rate**chain_length, 3)
