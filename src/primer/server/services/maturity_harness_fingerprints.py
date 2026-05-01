"""Harness configuration fingerprint helpers for maturity analytics."""

from collections import Counter
from hashlib import sha256
from typing import Any

from primer.common.facet_taxonomy import is_success_outcome
from primer.common.schemas import EngineerLeverageProfile, HarnessConfigurationFingerprint

DEFAULT_COMPOUND_RELIABILITY_CHAIN_LENGTH = 10


def context_signal_count(source_metadata: object) -> int:
    """Return the number of native context references captured for a session."""
    if not isinstance(source_metadata, dict):
        return 0
    native_telemetry = source_metadata.get("native_telemetry")
    if not isinstance(native_telemetry, dict):
        return 0
    context_usage = native_telemetry.get("context_usage")
    if isinstance(context_usage, dict):
        reference_count = context_usage.get("reference_count")
        if isinstance(reference_count, int | float):
            return max(int(reference_count), 0)
    return 0


def build_harness_configuration_fingerprints(
    *,
    source_metadata_rows: list[Any],
    per_session: dict[str, dict[str, int]],
    session_customization_fingerprint_parts: dict[str, set[str]],
    session_customization_labels: dict[str, set[str]],
    session_metrics: dict[str, dict[str, Any]],
    session_engineer: dict[str, tuple[str, str]],
    profile_by_engineer_id: dict[str, EngineerLeverageProfile],
    compound_reliability_chain_length: int = DEFAULT_COMPOUND_RELIABILITY_CHAIN_LENGTH,
) -> list[HarnessConfigurationFingerprint]:
    """Build compact fingerprints for repeated harness configurations."""
    session_source_metadata = {row.id: row.source_metadata or {} for row in source_metadata_rows}
    harness_fingerprint_data: dict[str, dict[str, Any]] = {}

    for row in source_metadata_rows:
        tools = per_session.get(row.id, {})
        if not tools and row.id not in session_customization_fingerprint_parts:
            continue
        tool_names = tuple(sorted(tool_name for tool_name, count in tools.items() if count > 0))
        customization_parts = tuple(
            sorted(session_customization_fingerprint_parts.get(row.id, set()))
        )
        customization_names = tuple(sorted(session_customization_labels.get(row.id, set())))
        permission_mode = row.permission_mode or "default"
        context_count = context_signal_count(session_source_metadata.get(row.id, {}))
        context_bucket = "context:present" if context_count > 0 else "context:none"
        raw_parts = [
            f"agent:{row.agent_type}",
            f"permission:{permission_mode}",
            *[f"tool:{tool}" for tool in tool_names],
            *[f"customization:{customization}" for customization in customization_parts],
            context_bucket,
        ]
        fingerprint_id = sha256("|".join(raw_parts).encode()).hexdigest()[:16]
        bucket = harness_fingerprint_data.setdefault(
            fingerprint_id,
            {
                "fingerprint_id": fingerprint_id,
                "agent_type": row.agent_type,
                "permission_mode": permission_mode,
                "sessions": set(),
                "engineers": set(),
                "success_sessions": set(),
                "leverage_scores": [],
                "tool_counts": [],
                "customization_counts": [],
                "context_signal_counts": [],
                "tools": Counter(),
                "customizations": Counter(),
                "signals": Counter(),
            },
        )
        bucket["sessions"].add(row.id)
        session_metric = session_metrics.get(row.id)
        if session_metric is not None:
            engineer_id_for_session = session_metric["engineer_id"]
            if engineer_id_for_session:
                bucket["engineers"].add(engineer_id_for_session)
            outcome = session_metric["outcome"]
            if outcome and is_success_outcome(outcome):
                bucket["success_sessions"].add(row.id)
        bucket["tool_counts"].append(len(tool_names))
        bucket["customization_counts"].append(len(customization_names))
        bucket["context_signal_counts"].append(context_count)
        bucket["tools"].update(tool_names)
        bucket["customizations"].update(customization_names)
        bucket["signals"].update(
            [
                f"agent:{row.agent_type}",
                f"permission:{permission_mode}",
                "context" if context_count > 0 else "no_context",
            ]
        )
        if row.id in session_engineer:
            engineer_id_for_session = session_engineer[row.id][0]
            profile = profile_by_engineer_id.get(engineer_id_for_session)
            if profile is not None:
                bucket["leverage_scores"].append(profile.leverage_score)

    return [
        HarnessConfigurationFingerprint(
            fingerprint_id=bucket["fingerprint_id"],
            label=(
                f"{bucket['agent_type']} / {bucket['permission_mode']} / "
                f"{round(sum(bucket['tool_counts']) / len(bucket['tool_counts']), 1)} tools"
            ),
            agent_type=bucket["agent_type"],
            permission_mode=bucket["permission_mode"],
            session_count=len(bucket["sessions"]),
            engineer_count=len(bucket["engineers"]),
            success_rate=(
                round(len(bucket["success_sessions"]) / len(bucket["sessions"]), 3)
                if bucket["sessions"]
                else None
            ),
            avg_leverage_score=(
                round(sum(bucket["leverage_scores"]) / len(bucket["leverage_scores"]), 1)
                if bucket["leverage_scores"]
                else 0.0
            ),
            compound_reliability_rate=_fingerprint_compound_rate(
                bucket,
                compound_reliability_chain_length,
            ),
            tool_count=round(sum(bucket["tool_counts"]) / len(bucket["tool_counts"]))
            if bucket["tool_counts"]
            else 0,
            customization_count=round(
                sum(bucket["customization_counts"]) / len(bucket["customization_counts"])
            )
            if bucket["customization_counts"]
            else 0,
            context_signal_count=round(
                sum(bucket["context_signal_counts"]) / len(bucket["context_signal_counts"])
            )
            if bucket["context_signal_counts"]
            else 0,
            top_tools=[tool for tool, _count in bucket["tools"].most_common(5)],
            top_customizations=[
                customization for customization, _count in bucket["customizations"].most_common(5)
            ],
            signals=[signal for signal, _count in bucket["signals"].most_common(5)],
        )
        for bucket in sorted(
            harness_fingerprint_data.values(),
            key=lambda item: (
                -len(item["sessions"]),
                -(
                    sum(item["leverage_scores"]) / len(item["leverage_scores"])
                    if item["leverage_scores"]
                    else 0.0
                ),
                item["fingerprint_id"],
            ),
        )
    ][:25]


def _fingerprint_compound_rate(bucket: dict[str, Any], chain_length: int) -> float | None:
    if not bucket["sessions"]:
        return None
    avg_steps = (
        sum(bucket["tool_counts"]) / len(bucket["tool_counts"]) if bucket["tool_counts"] else 0
    )
    if avg_steps <= 0:
        return None
    success_rate = len(bucket["success_sessions"]) / len(bucket["sessions"])
    per_step_rate = success_rate ** (1.0 / avg_steps)
    return round(per_step_rate**chain_length, 3)
