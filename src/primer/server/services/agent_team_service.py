from __future__ import annotations

from dataclasses import dataclass

from primer.server.services.delegation_graph_service import (
    DelegationEdgeRecord,
    extract_session_delegation_edges,
)

_TEAM_COORDINATION_EDGE_TYPES = {"team_setup", "team_message", "worktree_handoff"}


@dataclass(slots=True)
class AgentTeamDetectionRecord:
    coordination_mode: str
    delegation_edge_count: int
    distinct_targets: int
    target_nodes: list[str]
    edge_types: list[str]


def detect_session_agent_team(
    messages: list[object] | None,
    tool_usages: list[object] | None = None,
) -> AgentTeamDetectionRecord:
    edges = extract_session_delegation_edges(messages, tool_usages)
    return classify_agent_team_from_edges(edges)


def classify_agent_team_from_edges(
    edges: list[DelegationEdgeRecord],
) -> AgentTeamDetectionRecord:
    if not edges:
        return AgentTeamDetectionRecord(
            coordination_mode="solo",
            delegation_edge_count=0,
            distinct_targets=0,
            target_nodes=[],
            edge_types=[],
        )

    target_nodes = sorted({edge.target_node for edge in edges if edge.target_node})
    edge_types = sorted({edge.edge_type for edge in edges if edge.edge_type})

    coordination_mode = "delegated"
    if set(edge_types) & _TEAM_COORDINATION_EDGE_TYPES or len(target_nodes) >= 2:
        coordination_mode = "agent_team"

    return AgentTeamDetectionRecord(
        coordination_mode=coordination_mode,
        delegation_edge_count=len(edges),
        distinct_targets=len(target_nodes),
        target_nodes=target_nodes,
        edge_types=edge_types,
    )
