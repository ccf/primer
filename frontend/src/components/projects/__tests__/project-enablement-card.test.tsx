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
          playbook_templates: [
            {
              template_type: "legacy",
              title: "Legacy-system stabilization playbook",
              summary: "Front-load discovery and verify after each small edit.",
              recommended_workflow: "Debugging -> Verify -> Edit -> Verify",
              initial_steps: ["Trace the narrowest path first."],
              guardrails: ["Prefer reversible edits."],
              evidence: {},
            },
          ],
          recommendations: [
            {
              category: "tooling",
              title: "Stabilize recurring tooling failures",
              description: "Tooling is failing in repeated project sessions.",
              severity: "warning",
              evidence: { friction_type: "tool_error" },
              narrative: null,
            },
          ],
        }}
        teamId={null}
        projectName="primer"
      />,
    )

    expect(screen.getByText("Enablement Recommendations")).toBeInTheDocument()
    expect(screen.getByText("Playbook Templates")).toBeInTheDocument()
    expect(screen.getByText("Legacy-system stabilization playbook")).toBeInTheDocument()
    expect(screen.getByText("Stabilize recurring tooling failures")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "Create intervention" }))

    expect(
      screen.getByText("modal:Stabilize recurring tooling failures"),
    ).toBeInTheDocument()
  })
})
