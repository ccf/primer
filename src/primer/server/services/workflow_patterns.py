from collections import Counter

from primer.common.tool_classification import classify_tool

_SEARCH_HINTS = ("grep", "glob", "search", "find", "ripgrep")
_READ_HINTS = ("read", "fetch", "open", "cat", "view")
_EDIT_HINTS = ("edit", "write", "patch", "replace", "insert", "delete", "remove", "rename", "move")
_EXECUTE_HINTS = ("bash", "terminal", "exec", "command")
_DELEGATE_HINTS = ("task", "agent", "delegate", "team", "sendmessage", "send_message")
_INTEGRATE_HINTS = ("mcp", "plugin")


def infer_workflow_steps(
    tool_counts: Counter[str],
    has_commit: bool,
    *,
    execution_types: set[str] | None = None,
    recovery_strategies: set[str] | None = None,
    has_mutations: bool = False,
) -> list[str]:
    tool_names = set(tool_counts)
    steps: list[str] = []
    if any(_is_search_tool(name) for name in tool_names):
        steps.append("search")
    if any(_is_read_tool(name) for name in tool_names):
        steps.append("read")
    if has_mutations or any(_is_edit_tool(name) for name in tool_names):
        steps.append("edit")
    if execution_types or any(_is_execute_tool(name) for name in tool_names):
        steps.append("execute")
    if execution_types and "test" in execution_types:
        steps.append("test")
    if recovery_strategies and recovery_strategies.intersection({"edit_fix", "revert_or_reset"}):
        steps.append("fix")
    if any(is_delegate_tool(name) for name in tool_names):
        steps.append("delegate")
    if any(_is_integrate_tool(name) for name in tool_names):
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


def _normalized_tool_name(name: str) -> str:
    return name.strip().lower()


def _is_search_tool(name: str) -> bool:
    normalized = _normalized_tool_name(name)
    return classify_tool(name) == "search" or any(hint in normalized for hint in _SEARCH_HINTS)


def _is_read_tool(name: str) -> bool:
    normalized = _normalized_tool_name(name)
    return normalized in {"read", "webfetch"} or any(hint in normalized for hint in _READ_HINTS)


def _is_edit_tool(name: str) -> bool:
    normalized = _normalized_tool_name(name)
    return normalized in {"edit", "write", "notebookedit"} or any(
        hint in normalized for hint in _EDIT_HINTS
    )


def _is_execute_tool(name: str) -> bool:
    normalized = _normalized_tool_name(name)
    return normalized == "bash" or any(hint in normalized for hint in _EXECUTE_HINTS)


def is_delegate_tool(name: str) -> bool:
    normalized = _normalized_tool_name(name)
    return classify_tool(name) in {"orchestration", "skill"} or any(
        hint in normalized for hint in _DELEGATE_HINTS
    )


def _is_integrate_tool(name: str) -> bool:
    normalized = _normalized_tool_name(name)
    return classify_tool(name) == "mcp" or any(hint in normalized for hint in _INTEGRATE_HINTS)
