import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

vi.mock("@/components/interventions/intervention-form-modal", () => ({
  InterventionFormModal: ({
    open,
    recommendation,
  }: {
    open: boolean
    recommendation?: { title?: string } | null
  }) => (open ? <div>modal:{recommendation?.title}</div> : null),
}))

import { ProjectEnablementCard } from "@/components/projects/project-enablement-card"

describe("ProjectEnablementCard", () => {
  it("renders project recommendations and opens the intervention flow", () => {
    render(
      <ProjectEnablementCard
        enablement={{
          linked_repository_count: 1,
          agent_type_counts: { claude_code: 2 },
          session_type_counts: { implementation: 2 },
          permission_mode_counts: { "on-request": 2 },
          top_tools: ["Edit", "Bash"],
          top_models: ["claude-sonnet-4"],
          recommendations: [
            {
              category: "tooling",
              title: "Stabilize recurring tooling failures",
              description: "Tooling is failing in repeated project sessions.",
              severity: "warning",
              evidence: { friction_type: "tool_error" },
            },
          ],
        }}
        teamId={null}
        projectName="primer"
      />,
    )

    expect(screen.getByText("Enablement Recommendations")).toBeInTheDocument()
    expect(screen.getByText("Stabilize recurring tooling failures")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "Create intervention" }))

    expect(
      screen.getByText("modal:Stabilize recurring tooling failures"),
    ).toBeInTheDocument()
  })
})
