import { render, screen } from "@testing-library/react"

import { CoachingProgramMeasurementSection } from "@/components/interventions/coaching-program-measurement"

describe("CoachingProgramMeasurementSection", () => {
  it("renders an empty state", () => {
    render(<CoachingProgramMeasurementSection programs={[]} />)

    expect(
      screen.getByText("No measured onboarding or training programs are available yet."),
    ).toBeInTheDocument()
  })

  it("renders coaching program cards", () => {
    render(
      <CoachingProgramMeasurementSection
        programs={[
          {
            intervention_id: "int-1",
            title: "Roll out the debugging checklist",
            target_cohort: "new hires",
            owner_name: "Lead",
            project_name: "primer",
            hypothesis: "A checklist should reduce triage friction.",
            success_criteria: "Reduce friction events by 25%.",
            measured: true,
            improved: true,
            completion_days: 3.5,
            success_rate_delta: 0.2,
            friction_delta: 2,
            findings_per_pr_delta: 0.5,
            avg_cost_per_session_delta: -0.3,
          },
        ]}
      />,
    )

    expect(screen.getByText("Coaching Program Measurement")).toBeInTheDocument()
    expect(screen.getByText("Roll out the debugging checklist")).toBeInTheDocument()
    expect(screen.getAllByText("Improved").length).toBeGreaterThan(0)
    expect(screen.getByText("Success Criteria")).toBeInTheDocument()
  })
})
