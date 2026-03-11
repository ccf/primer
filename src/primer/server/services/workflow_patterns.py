from collections import Counter

from primer.common.tool_classification import classify_tool


def infer_workflow_steps(tool_counts: Counter[str], has_commit: bool) -> list[str]:
    tool_names = set(tool_counts)
    steps: list[str] = []
    if any(classify_tool(name) == "search" for name in tool_names):
        steps.append("search")
    if tool_names.intersection({"Read", "WebFetch"}):
        steps.append("read")
    if tool_names.intersection({"Edit", "Write", "NotebookEdit"}):
        steps.append("edit")
    if "Bash" in tool_names:
        steps.append("execute")
    if any(classify_tool(name) in {"orchestration", "skill"} for name in tool_names):
        steps.append("delegate")
    if any(classify_tool(name) == "mcp" for name in tool_names):
        steps.append("integrate")
    if has_commit:
        steps.append("ship")
    return steps


def workflow_fingerprint_id(session_type: str | None, steps: list[str]) -> str:
    normalized_type = session_type or "general"
    normalized_steps = "+".join(steps) if steps else "reasoning"
    return f"{normalized_type}::{normalized_steps}"


def workflow_fingerprint_label(session_type: str | None, steps: list[str]) -> str:
    type_label = (session_type or "general").replace("_", " ")
    step_label = " -> ".join(steps) if steps else "reasoning"
    return f"{type_label}: {step_label}"
