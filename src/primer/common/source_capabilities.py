from dataclasses import dataclass

from primer.common.schemas import AgentType


@dataclass(frozen=True)
class AgentCapability:
    agent_type: AgentType
    supports_transcript: bool
    supports_tool_calls: bool
    supports_model_usage: bool
    supports_facets: bool
    supports_native_discovery: bool


CAPABILITIES: dict[AgentType, AgentCapability] = {
    "claude_code": AgentCapability(
        agent_type="claude_code",
        supports_transcript=True,
        supports_tool_calls=True,
        supports_model_usage=True,
        supports_facets=True,
        supports_native_discovery=True,
    ),
    "codex_cli": AgentCapability(
        agent_type="codex_cli",
        supports_transcript=True,
        supports_tool_calls=True,
        supports_model_usage=True,
        supports_facets=False,
        supports_native_discovery=True,
    ),
    "gemini_cli": AgentCapability(
        agent_type="gemini_cli",
        supports_transcript=True,
        supports_tool_calls=True,
        supports_model_usage=True,
        supports_facets=False,
        supports_native_discovery=True,
    ),
    "cursor": AgentCapability(
        agent_type="cursor",
        supports_transcript=True,
        supports_tool_calls=False,
        supports_model_usage=False,
        supports_facets=False,
        supports_native_discovery=False,
    ),
}


def get_capability_for(agent_type: str) -> AgentCapability | None:
    return CAPABILITIES.get(agent_type)
