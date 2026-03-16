import { render, screen } from "@testing-library/react"

import { WorkflowCostTable } from "@/components/finops/workflow-cost-table"

describe("WorkflowCostTable", () => {
  it("renders an empty state when no workflow rows exist", () => {
    render(<WorkflowCostTable rows={[]} />)

    expect(screen.getByText("No workflow cost attribution data available yet.")).toBeInTheDocument()
  })

  it("groups workflow cost rows by dimension", () => {
    render(
      <WorkflowCostTable
        rows={[
          {
            dimension: "workflow_archetype",
            label: "debugging",
            session_count: 2,
            total_estimated_cost: 12.5,
            avg_cost_per_session: 6.25,
            cost_per_successful_outcome: 12.5,
          },
          {
            dimension: "workflow_fingerprint",
            label: "bug fix: read -> edit -> ship",
            session_count: 1,
            total_estimated_cost: 4.2,
            avg_cost_per_session: 4.2,
            cost_per_successful_outcome: 4.2,
          },
        ]}
      />,
    )

    expect(screen.getByText("Workflow Archetype")).toBeInTheDocument()
    expect(screen.getByText("Workflow Fingerprint")).toBeInTheDocument()
    expect(screen.getByText("Debugging")).toBeInTheDocument()
    expect(screen.getByText("Bug Fix: Read -> Edit -> Ship")).toBeInTheDocument()
  })
})
