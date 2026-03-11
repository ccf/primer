from dataclasses import dataclass
from typing import Literal

from primer.common.schemas import AgentType, TelemetryParity

TelemetryField = Literal[
    "transcript",
    "tool_calls",
    "model_usage",
    "facets",
    "native_discovery",
]


@dataclass(frozen=True)
class AgentCapability:
    agent_type: AgentType
    transcript: TelemetryParity
    tool_calls: TelemetryParity
    model_usage: TelemetryParity
    facets: TelemetryParity
    native_discovery: TelemetryParity

    def parity_for(self, field_name: TelemetryField) -> TelemetryParity:
        return getattr(self, field_name)

    def is_available(self, field_name: TelemetryField) -> bool:
        return self.parity_for(field_name) != "unavailable"

    def is_required(self, field_name: TelemetryField) -> bool:
        return self.parity_for(field_name) == "required"

    @property
    def supports_transcript(self) -> bool:
        return self.is_available("transcript")

    @property
    def supports_tool_calls(self) -> bool:
        return self.is_available("tool_calls")

    @property
    def supports_model_usage(self) -> bool:
        return self.is_available("model_usage")

    @property
    def supports_facets(self) -> bool:
        return self.is_available("facets")

    @property
    def supports_native_discovery(self) -> bool:
        return self.is_available("native_discovery")


CAPABILITIES: dict[AgentType, AgentCapability] = {
    "claude_code": AgentCapability(
        agent_type="claude_code",
        transcript="required",
        tool_calls="required",
        model_usage="required",
        facets="required",
        native_discovery="required",
    ),
    "codex_cli": AgentCapability(
        agent_type="codex_cli",
        transcript="required",
        tool_calls="required",
        model_usage="required",
        facets="optional",
        native_discovery="required",
    ),
    "gemini_cli": AgentCapability(
        agent_type="gemini_cli",
        transcript="required",
        tool_calls="required",
        model_usage="required",
        facets="optional",
        native_discovery="required",
    ),
    "cursor": AgentCapability(
        agent_type="cursor",
        transcript="required",
        tool_calls="optional",
        model_usage="optional",
        facets="optional",
        native_discovery="required",
    ),
}


def get_capability_for(agent_type: str) -> AgentCapability | None:
    return CAPABILITIES.get(agent_type)
