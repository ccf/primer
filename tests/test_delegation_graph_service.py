from primer.server.services.delegation_graph_service import extract_session_delegation_edges


def test_extract_session_delegation_edges_from_messages():
    messages = [
        {
            "ordinal": 1,
            "tool_calls": [
                {
                    "name": "Task",
                    "input_preview": '{"subagent_type":"reviewer","prompt":"Review the diff"}',
                },
                {
                    "name": "SendMessage",
                    "input_preview": '{"recipient":"qa","message":"Smoke test this change"}',
                },
            ],
        }
    ]

    edges = extract_session_delegation_edges(messages)

    assert [(edge.edge_type, edge.target_node, edge.call_count) for edge in edges] == [
        ("subagent_task", "reviewer", 1),
        ("team_message", "qa", 1),
    ]
    assert edges[0].prompt_preview == "Review the diff"
    assert edges[1].prompt_preview == "Smoke test this change"


def test_extract_session_delegation_edges_falls_back_to_tool_usages():
    tool_usages = [
        {"tool_name": "Task:explore", "call_count": 2},
        {"tool_name": "SendMessage", "call_count": 1},
    ]

    edges = extract_session_delegation_edges([], tool_usages)

    assert [(edge.edge_type, edge.target_node, edge.call_count) for edge in edges] == [
        ("subagent_task", "explore", 2),
        ("team_message", "team", 1),
    ]
