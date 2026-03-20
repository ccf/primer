import { render, screen } from "@testing-library/react"

import { ReuseOpportunityCards } from "@/components/growth/reuse-opportunity-cards"

describe("ReuseOpportunityCards", () => {
  it("renders an empty state", () => {
    render(<ReuseOpportunityCards assets={[]} />)

    expect(screen.getByText("No high-value reuse opportunities identified yet.")).toBeInTheDocument()
  })

  it("renders underused assets", () => {
    render(
      <ReuseOpportunityCards
        assets={[
          {
            identifier: "bugfix",
            customization_type: "template",
            provenance: "repo_defined",
            source_classification: "custom",
            engineer_count: 1,
            session_count: 2,
            total_invocations: 2,
            adoption_rate: 0.25,
            success_rate: 1,
            avg_session_cost: 0.08,
            cost_per_successful_outcome: 0.08,
            primary_workflow_archetype: "debugging",
            workflow_archetypes: ["debugging", "feature_delivery"],
            top_projects: ["primer"],
          },
        ]}
      />,
    )

    expect(screen.getByText("bugfix")).toBeInTheDocument()
    expect(screen.getByText("Template")).toBeInTheDocument()
    expect(screen.getByText("25%")).toBeInTheDocument()
    expect(screen.getByText("100%")).toBeInTheDocument()
    expect(screen.getByText("$0.08")).toBeInTheDocument()
    expect(screen.getByText("Debugging")).toBeInTheDocument()
  })
})
