from primer.server.services.agent_team_service import (
    classify_agent_team_from_edges,
    detect_session_agent_team,
)
from primer.server.services.delegation_graph_service import DelegationEdgeRecord


def test_detect_session_agent_team_marks_solo_without_edges():
    record = detect_session_agent_team([], [])

    assert record.coordination_mode == "solo"
    assert record.delegation_edge_count == 0
    assert record.target_nodes == []


def test_detect_session_agent_team_marks_delegated_for_single_subagent():
    record = detect_session_agent_team(
        [
            {
                "ordinal": 1,
                "tool_calls": [
                    {
                        "name": "Task",
                        "input_preview": '{"subagent_type":"reviewer","prompt":"Review the diff"}',
                    }
                ],
            }
        ]
    )

    assert record.coordination_mode == "delegated"
    assert record.delegation_edge_count == 1
    assert record.target_nodes == ["reviewer"]


def test_classify_agent_team_from_edges_marks_agent_team_for_multiple_targets():
    record = classify_agent_team_from_edges(
        [
            DelegationEdgeRecord(
                source_node="primary_agent",
                target_node="reviewer",
                edge_type="subagent_task",
                tool_name="Task:reviewer",
                call_count=2,
            ),
            DelegationEdgeRecord(
                source_node="primary_agent",
                target_node="qa",
                edge_type="team_message",
                tool_name="SendMessage",
                call_count=1,
            ),
        ]
    )

    assert record.coordination_mode == "agent_team"
    assert record.delegation_edge_count == 2
    assert record.distinct_targets == 2
