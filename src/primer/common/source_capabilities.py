from dataclasses import dataclass
from typing import Literal

from primer.common.schemas import AgentType, TelemetryParity

TelemetryField = Literal[
    "transcript",
    "tool_calls",
    "model_usage",
    "facets",
    "native_discovery",
    "approval_signals",
    "change_signals",
    "context_usage",
]


@dataclass(frozen=True)
class AgentCapability:
    agent_type: AgentType
    transcript: TelemetryParity
    tool_calls: TelemetryParity
    model_usage: TelemetryParity
    facets: TelemetryParity
    native_discovery: TelemetryParity
    approval_signals: TelemetryParity
    change_signals: TelemetryParity
    context_usage: TelemetryParity

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

    @property
    def supports_approval_signals(self) -> bool:
        return self.is_available("approval_signals")

    @property
    def supports_change_signals(self) -> bool:
        return self.is_available("change_signals")

    @property
    def supports_context_usage(self) -> bool:
        return self.is_available("context_usage")


CAPABILITIES: dict[AgentType, AgentCapability] = {
    "claude_code": AgentCapability(
        agent_type="claude_code",
        transcript="required",
        tool_calls="required",
        model_usage="required",
        facets="required",
        native_discovery="required",
        approval_signals="unavailable",
        change_signals="unavailable",
        context_usage="unavailable",
    ),
    "codex_cli": AgentCapability(
        agent_type="codex_cli",
        transcript="required",
        tool_calls="required",
        model_usage="required",
        facets="optional",
        native_discovery="required",
        approval_signals="unavailable",
        change_signals="unavailable",
        context_usage="unavailable",
    ),
    "gemini_cli": AgentCapability(
        agent_type="gemini_cli",
        transcript="required",
        tool_calls="required",
        model_usage="required",
        facets="optional",
        native_discovery="required",
        approval_signals="unavailable",
        change_signals="unavailable",
        context_usage="unavailable",
    ),
    "cursor": AgentCapability(
        agent_type="cursor",
        transcript="required",
        tool_calls="optional",
        model_usage="optional",
        facets="optional",
        native_discovery="required",
        approval_signals="optional",
        change_signals="optional",
        context_usage="optional",
    ),
}


def get_capability_for(agent_type: str) -> AgentCapability | None:
    return CAPABILITIES.get(agent_type)


def get_agent_types_with_capability(capability_name: str) -> list[AgentType]:
    return [
        agent_type
        for agent_type, capability in CAPABILITIES.items()
        if getattr(capability, capability_name)
    ]
