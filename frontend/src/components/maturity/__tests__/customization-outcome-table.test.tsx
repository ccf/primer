import { render, screen } from "@testing-library/react"

import { CustomizationOutcomeTable } from "@/components/maturity/customization-outcome-table"

describe("CustomizationOutcomeTable", () => {
  it("renders an empty state", () => {
    render(<CustomizationOutcomeTable rows={[]} />)

    expect(screen.getByText("No customization outcome attribution available yet.")).toBeInTheDocument()
  })

  it("renders attribution rows", () => {
    render(
      <CustomizationOutcomeTable
        rows={[
          {
            dimension: "customization",
            label: "github",
            customization_type: "mcp",
            provenance: "user_local",
            support_engineer_count: 2,
            support_session_count: 4,
            avg_effectiveness_score: 88.2,
            avg_leverage_score: 91.4,
            avg_success_rate: 1,
            avg_cost_per_successful_outcome: 0.42,
            avg_pr_merge_rate: 1,
            cohort_share: 0.5,
          },
        ]}
      />,
    )

    expect(screen.getByText("github")).toBeInTheDocument()
    expect(screen.getByText("Customization")).toBeInTheDocument()
    expect(screen.getByText("Mcp")).toBeInTheDocument()
    expect(screen.getByText("User Local")).toBeInTheDocument()
    expect(screen.getAllByText("100%")).toHaveLength(2)
    expect(screen.getByText("$0.42")).toBeInTheDocument()
  })
})
