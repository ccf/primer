import { render, screen } from "@testing-library/react"

import { ReusableAssetTable } from "@/components/growth/reusable-asset-table"

describe("ReusableAssetTable", () => {
  it("renders an empty state", () => {
    render(<ReusableAssetTable assets={[]} />)

    expect(
      screen.getByText("No reusable skills, commands, or templates detected yet."),
    ).toBeInTheDocument()
  })

  it("renders reusable assets", () => {
    render(
      <ReusableAssetTable
        assets={[
          {
            identifier: "review-pr",
            customization_type: "skill",
            provenance: "repo_defined",
            source_classification: "custom",
            engineer_count: 2,
            session_count: 3,
            total_invocations: 5,
            adoption_rate: 0.5,
            success_rate: 1,
            avg_session_cost: 0.12,
            cost_per_successful_outcome: 0.12,
            primary_workflow_archetype: "debugging",
            workflow_archetypes: ["debugging"],
            top_projects: ["primer"],
          },
        ]}
      />,
    )

    expect(screen.getByText("review-pr")).toBeInTheDocument()
    expect(screen.getByText("Skill")).toBeInTheDocument()
    expect(screen.getByText("Repo Defined")).toBeInTheDocument()
    expect(screen.getByText("50%")).toBeInTheDocument()
    expect(screen.getByText("100%")).toBeInTheDocument()
    expect(screen.getByText("$0.12")).toBeInTheDocument()
    expect(screen.getByText("Debugging")).toBeInTheDocument()
    expect(screen.getByText("primer")).toBeInTheDocument()
  })
})
