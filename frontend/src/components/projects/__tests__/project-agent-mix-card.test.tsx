import { render, screen } from "@testing-library/react"

import { ProjectAgentMixCard } from "@/components/projects/project-agent-mix-card"

describe("ProjectAgentMixCard", () => {
  it("renders agent comparison metrics and telemetry fallbacks", () => {
    render(
      <ProjectAgentMixCard
        agentMix={{
          total_sessions: 6,
          compared_agents: 2,
          dominant_agent_type: "cursor",
          entries: [
            {
              agent_type: "cursor",
              session_count: 4,
              share_of_sessions: 0.667,
              unique_engineers: 2,
              success_rate: 0.75,
              friction_rate: 0.25,
              avg_health_score: 71.4,
              avg_cost_per_session: null,
              top_tools: [],
              top_models: [],
            },
            {
              agent_type: "claude_code",
              session_count: 2,
              share_of_sessions: 0.333,
              unique_engineers: 1,
              success_rate: 1.0,
              friction_rate: 0.0,
              avg_health_score: 88.2,
              avg_cost_per_session: 2.35,
              top_tools: ["Edit", "Bash"],
              top_models: ["claude-sonnet-4"],
            },
          ],
        }}
      />,
    )

    expect(screen.getByText("Agent Mix Comparison")).toBeInTheDocument()
    expect(screen.getAllByText("Cursor").length).toBeGreaterThan(0)
    expect(screen.getByText("Claude Code")).toBeInTheDocument()
    expect(screen.getByText("67% share")).toBeInTheDocument()
    expect(screen.getByText("75%")).toBeInTheDocument()
    expect(screen.getByText("$2.35")).toBeInTheDocument()
    expect(screen.getAllByText("No model telemetry").length).toBeGreaterThan(0)
    expect(screen.getAllByText("No tool telemetry").length).toBeGreaterThan(0)
    expect(screen.getByText("Edit")).toBeInTheDocument()
    expect(screen.getByText("claude-sonnet-4")).toBeInTheDocument()
  })
})
