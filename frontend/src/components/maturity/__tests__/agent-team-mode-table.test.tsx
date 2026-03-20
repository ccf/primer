import { render, screen } from "@testing-library/react"

import { AgentTeamModeTable } from "@/components/maturity/agent-team-mode-table"

describe("AgentTeamModeTable", () => {
  it("renders an empty state", () => {
    render(<AgentTeamModeTable rows={[]} />)

    expect(screen.getByText("No agent team coordination patterns detected yet.")).toBeInTheDocument()
  })

  it("renders coordination mode rows", () => {
    render(
      <AgentTeamModeTable
        rows={[
          {
            coordination_mode: "agent_team",
            session_count: 4,
            engineer_count: 2,
            session_share: 0.4,
            success_rate: 0.75,
            avg_cost_per_session: 0.21,
            avg_delegation_edges: 3.5,
            top_targets: ["reviewer", "qa"],
            top_workflow_archetypes: ["debugging"],
          },
        ]}
      />,
    )

    expect(screen.getByText("Agent Team")).toBeInTheDocument()
    expect(screen.getByText("40% of sessions")).toBeInTheDocument()
    expect(screen.getByText("75%")).toBeInTheDocument()
    expect(screen.getByText("$0.21")).toBeInTheDocument()
    expect(screen.getByText("3.50")).toBeInTheDocument()
    expect(screen.getByText("reviewer")).toBeInTheDocument()
  })
})
