from __future__ import annotations

from dataclasses import dataclass

from primer.server.services.session_signal_parsing import (
    load_json_object,
    message_payload,
    normalize_tool_name,
)

_PROMPT_KEYS = ("prompt", "message", "request", "task", "goal", "content")
_TARGET_KEYS = (
    "subagent_type",
    "subagent",
    "agent",
    "recipient",
    "target",
    "team_name",
    "team",
    "worktree",
    "path",
    "name",
)


@dataclass(slots=True)
class DelegationEdgeRecord:
    source_node: str
    target_node: str
    edge_type: str
    tool_name: str
    call_count: int
    prompt_preview: str | None = None
    ordinal: int = 0

    def key(self) -> tuple[str, str, str]:
        return (self.source_node, self.target_node, self.edge_type)


def extract_session_delegation_edges(
    messages: list[object] | None,
    tool_usages: list[object] | None = None,
) -> list[DelegationEdgeRecord]:
    message_edges = _dedupe_edges(_edges_from_messages(messages or []))
    if not tool_usages:
        return message_edges

    fallback_edges = _dedupe_edges(_edges_from_tool_usages(tool_usages))
    if not message_edges:
        return fallback_edges

    message_keys = {edge.key() for edge in message_edges}
    for edge in fallback_edges:
        if edge.key() not in message_keys:
            message_edges.append(edge)
    return sorted(message_edges, key=lambda edge: (edge.ordinal, edge.edge_type, edge.target_node))


def _edges_from_messages(messages: list[object]) -> list[DelegationEdgeRecord]:
    edges: list[DelegationEdgeRecord] = []
    for message in messages:
        payload = message_payload(message)
        if payload is None:
            continue
        ordinal = int(payload.get("ordinal", 0) or 0)
        tool_calls = payload.get("tool_calls")
        if not isinstance(tool_calls, list):
            continue
        for tool_call in tool_calls:
            edge = _edge_from_tool_call(tool_call, ordinal)
            if edge is not None:
                edges.append(edge)
    return edges


def _edge_from_tool_call(tool_call: object, ordinal: int) -> DelegationEdgeRecord | None:
    if not isinstance(tool_call, dict):
        return None

    raw_name = tool_call.get("name")
    if not isinstance(raw_name, str) or not raw_name:
        return None

    input_preview = tool_call.get("input_preview")
    parsed_preview = (
        load_json_object(input_preview) if isinstance(input_preview, str) else input_preview
    )
    prompt_preview = _extract_preview_text(parsed_preview, input_preview)

    if raw_name.startswith("Task:"):
        return DelegationEdgeRecord(
            source_node="primary_agent",
            target_node=raw_name.split(":", 1)[1].strip() or "task",
            edge_type="subagent_task",
            tool_name=raw_name,
            call_count=1,
            prompt_preview=prompt_preview,
            ordinal=ordinal,
        )
    if raw_name == "Task":
        return DelegationEdgeRecord(
            source_node="primary_agent",
            target_node=_extract_target(parsed_preview, fallback="task"),
            edge_type="subagent_task",
            tool_name=raw_name,
            call_count=1,
            prompt_preview=prompt_preview,
            ordinal=ordinal,
        )
    if raw_name == "Agent":
        return DelegationEdgeRecord(
            source_node="primary_agent",
            target_node=_extract_target(parsed_preview, fallback="agent"),
            edge_type="agent_spawn",
            tool_name=raw_name,
            call_count=1,
            prompt_preview=prompt_preview,
            ordinal=ordinal,
        )
    if raw_name == "TeamCreate":
        return DelegationEdgeRecord(
            source_node="primary_agent",
            target_node=_extract_target(parsed_preview, fallback="team"),
            edge_type="team_setup",
            tool_name=raw_name,
            call_count=1,
            prompt_preview=prompt_preview,
            ordinal=ordinal,
        )
    if raw_name == "SendMessage":
        return DelegationEdgeRecord(
            source_node="primary_agent",
            target_node=_extract_target(parsed_preview, fallback="team"),
            edge_type="team_message",
            tool_name=raw_name,
            call_count=1,
            prompt_preview=prompt_preview,
            ordinal=ordinal,
        )
    if raw_name == "EnterWorktree":
        return DelegationEdgeRecord(
            source_node="primary_agent",
            target_node=_extract_target(parsed_preview, fallback="worktree"),
            edge_type="worktree_handoff",
            tool_name=raw_name,
            call_count=1,
            prompt_preview=prompt_preview,
            ordinal=ordinal,
        )
    return None


def _edges_from_tool_usages(tool_usages: list[object]) -> list[DelegationEdgeRecord]:
    edges: list[DelegationEdgeRecord] = []
    for usage in tool_usages:
        tool_name = (
            usage.get("tool_name") if isinstance(usage, dict) else getattr(usage, "tool_name", None)
        )
        call_count = (
            usage.get("call_count", 0)
            if isinstance(usage, dict)
            else getattr(usage, "call_count", 0)
        )
        if not isinstance(tool_name, str) or not tool_name:
            continue
        try:
            normalized_count = max(int(call_count), 0)
        except (TypeError, ValueError):
            normalized_count = 0
        if normalized_count <= 0:
            continue

        if tool_name.startswith("Task:"):
            edges.append(
                DelegationEdgeRecord(
                    source_node="primary_agent",
                    target_node=tool_name.split(":", 1)[1].strip() or "task",
                    edge_type="subagent_task",
                    tool_name=tool_name,
                    call_count=normalized_count,
                )
            )
            continue
        normalized_name = normalize_tool_name(tool_name)
        if normalized_name == "task":
            edges.append(
                DelegationEdgeRecord(
                    source_node="primary_agent",
                    target_node="task",
                    edge_type="subagent_task",
                    tool_name=tool_name,
                    call_count=normalized_count,
                )
            )
        elif normalized_name == "agent":
            edges.append(
                DelegationEdgeRecord(
                    source_node="primary_agent",
                    target_node="agent",
                    edge_type="agent_spawn",
                    tool_name=tool_name,
                    call_count=normalized_count,
                )
            )
        elif normalized_name == "teamcreate":
            edges.append(
                DelegationEdgeRecord(
                    source_node="primary_agent",
                    target_node="team",
                    edge_type="team_setup",
                    tool_name=tool_name,
                    call_count=normalized_count,
                )
            )
        elif normalized_name == "sendmessage":
            edges.append(
                DelegationEdgeRecord(
                    source_node="primary_agent",
                    target_node="team",
                    edge_type="team_message",
                    tool_name=tool_name,
                    call_count=normalized_count,
                )
            )
        elif normalized_name == "enterworktree":
            edges.append(
                DelegationEdgeRecord(
                    source_node="primary_agent",
                    target_node="worktree",
                    edge_type="worktree_handoff",
                    tool_name=tool_name,
                    call_count=normalized_count,
                )
            )
    return edges


def _dedupe_edges(edges: list[DelegationEdgeRecord]) -> list[DelegationEdgeRecord]:
    merged: dict[tuple[str, str, str], DelegationEdgeRecord] = {}
    for edge in edges:
        existing = merged.get(edge.key())
        if existing is None:
            merged[edge.key()] = edge
            continue
        merged[edge.key()] = DelegationEdgeRecord(
            source_node=edge.source_node,
            target_node=edge.target_node,
            edge_type=edge.edge_type,
            tool_name=(
                edge.tool_name
                if len(edge.tool_name or "") > len(existing.tool_name or "")
                else existing.tool_name
            ),
            call_count=existing.call_count + edge.call_count,
            prompt_preview=existing.prompt_preview or edge.prompt_preview,
            ordinal=min(existing.ordinal, edge.ordinal),
        )
    return list(merged.values())


def _extract_target(parsed_preview: object, *, fallback: str) -> str:
    if isinstance(parsed_preview, dict):
        for key in _TARGET_KEYS:
            value = parsed_preview.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return fallback


def _extract_preview_text(parsed_preview: object, raw_preview: object) -> str | None:
    if isinstance(parsed_preview, dict):
        for key in _PROMPT_KEYS:
            value = parsed_preview.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()[:200]
    if isinstance(raw_preview, str) and raw_preview.strip() and raw_preview[0] != "{":
        return raw_preview.strip()[:200]
    return None
