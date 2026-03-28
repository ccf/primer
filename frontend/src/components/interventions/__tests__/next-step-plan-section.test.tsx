import { render, screen } from "@testing-library/react"
import { NextStepPlanSection } from "@/components/interventions/next-step-plan-section"
import type { NextStepPlanResponse } from "@/types/api"

const samplePlan: NextStepPlanResponse = {
  scope_label: "Platform",
  summary: "2 next-step actions synthesized from recent alerts, narratives, and project findings.",
  generated_at: "2026-03-28T00:00:00Z",
  actions: [
    {
      action_id: "recommendation:workflow:debugging",
      title: "Turn the best workflow into a project playbook",
      description: "Document the strongest debugging path for the repo.",
      priority: "high",
      source_type: "recommendation",
      source_title: "workflow",
      category: "workflow",
      severity: "warning",
      project_name: "primer",
      evidence: {},
      narrative: {
        why_this_helps: "It standardizes the highest-success workflow for similar work.",
        evidence_summary: "Backed by the top debugging fingerprint this month.",
        expected_impact: "More consistent recoveries.",
      },
    },
  ],
}

describe("NextStepPlanSection", () => {
  it("renders narrative details when present", () => {
    render(<NextStepPlanSection plan={samplePlan} />)

    expect(screen.getByText("Turn the best workflow into a project playbook")).toBeInTheDocument()
    expect(screen.getByText("Why this helps")).toBeInTheDocument()
    expect(
      screen.getByText("It standardizes the highest-success workflow for similar work."),
    ).toBeInTheDocument()
    expect(screen.getByText(/Likely impact:/)).toBeInTheDocument()
  })

  it("renders the empty state summary", () => {
    render(
      <NextStepPlanSection
        plan={{ ...samplePlan, summary: "Nothing urgent right now.", actions: [] }}
      />,
    )

    expect(screen.getByText("Nothing urgent right now.")).toBeInTheDocument()
  })
})
