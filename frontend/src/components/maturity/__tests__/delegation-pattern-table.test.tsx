import { render, screen } from "@testing-library/react"

import { DelegationPatternTable } from "@/components/maturity/delegation-pattern-table"

describe("DelegationPatternTable", () => {
  it("renders an empty state", () => {
    render(<DelegationPatternTable rows={[]} />)

    expect(screen.getByText("No delegation patterns detected yet.")).toBeInTheDocument()
  })

  it("renders delegation pattern rows", () => {
    render(
      <DelegationPatternTable
        rows={[
          {
            target_node: "reviewer",
            edge_type: "subagent_task",
            session_count: 3,
            engineer_count: 2,
            total_calls: 5,
            success_rate: 1,
            top_workflow_archetypes: ["debugging", "feature_delivery"],
          },
        ]}
      />,
    )

    expect(screen.getByText("reviewer")).toBeInTheDocument()
    expect(screen.getByText("Subagent Task")).toBeInTheDocument()
    expect(screen.getByText("5")).toBeInTheDocument()
    expect(screen.getByText("100%")).toBeInTheDocument()
    expect(screen.getByText("Debugging")).toBeInTheDocument()
  })
})
