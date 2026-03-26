import { render, screen } from "@testing-library/react"

import { ModelChoiceOpportunityTable } from "@/components/finops/model-choice-opportunity-table"

describe("ModelChoiceOpportunityTable", () => {
  it("renders an empty state when no opportunities exist", () => {
    render(<ModelChoiceOpportunityTable opportunities={[]} totalSavingsMonthly={0} />)

    expect(
      screen.getByText("No clear model downshift opportunities found for this period yet."),
    ).toBeInTheDocument()
  })

  it("renders scored opportunities", () => {
    render(
      <ModelChoiceOpportunityTable
        totalSavingsMonthly={14.2}
        opportunities={[
          {
            workflow_archetype: "debugging",
            current_model: "claude-opus-4-20250514",
            recommended_model: "claude-sonnet-4-5-20250929",
            current_session_count: 8,
            supporting_session_count: 12,
            current_success_rate: 0.82,
            recommended_success_rate: 0.84,
            current_avg_cost: 4.8,
            recommended_avg_cost: 1.1,
            period_savings_estimate: 22.4,
            monthly_savings_estimate: 14.2,
            confidence: "high",
            rationale: "Peers get similar results with Sonnet for debugging work.",
          },
        ]}
      />,
    )

    expect(screen.getByText("Model choice opportunities")).toBeInTheDocument()
    expect(
      screen.getByText("claude-opus-4-20250514 -> claude-sonnet-4-5-20250929"),
    ).toBeInTheDocument()
    expect(screen.getByText("Debugging")).toBeInTheDocument()
    expect(screen.getByText("High confidence")).toBeInTheDocument()
    expect(screen.getAllByText("$14.20")).toHaveLength(2)
  })
})
