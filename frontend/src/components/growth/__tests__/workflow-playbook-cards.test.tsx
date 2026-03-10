import { render, screen } from "@testing-library/react"

import { WorkflowPlaybookCards } from "@/components/growth/workflow-playbook-cards"

describe("WorkflowPlaybookCards", () => {
  it("renders playbook evidence, steps, and watch-outs", () => {
    render(
      <WorkflowPlaybookCards
        playbooks={[
          {
            playbook_id: "team:implementation::search+read+edit+execute",
            title: "implementation: search -> read -> edit -> execute",
            summary:
              "Teammates repeatedly use implementation: search -> read -> edit -> execute across 4 sessions from 2 peers with 100% success.",
            scope: "team",
            adoption_state: "not_used",
            session_type: "implementation",
            steps: ["search", "read", "edit", "execute"],
            recommended_tools: ["Grep", "Read", "Edit", "Bash"],
            caution_friction_types: ["context_switching"],
            example_projects: ["primer", "frontend-shell"],
            supporting_session_count: 4,
            supporting_peer_count: 2,
            success_rate: 1,
            friction_free_rate: 0.75,
            avg_duration_seconds: 1800,
            engineer_usage_count: 0,
          },
        ]}
      />,
    )

    expect(screen.getByText("implementation: search -> read -> edit -> execute")).toBeInTheDocument()
    expect(screen.getByText("not used")).toBeInTheDocument()
    expect(screen.getByText("100%")).toBeInTheDocument()
    expect(screen.getByText("75%")).toBeInTheDocument()
    expect(screen.getByText("Grep")).toBeInTheDocument()
    expect(screen.getByText("context switching")).toBeInTheDocument()
    expect(screen.getByText("frontend-shell")).toBeInTheDocument()
  })

  it("renders an empty state", () => {
    render(<WorkflowPlaybookCards playbooks={[]} />)

    expect(screen.getByText("No peer workflow playbooks available yet.")).toBeInTheDocument()
  })
})
