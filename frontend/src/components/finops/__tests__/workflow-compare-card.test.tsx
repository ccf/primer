import { fireEvent, render, screen } from "@testing-library/react"

import { WorkflowCompareCard } from "@/components/finops/workflow-compare-card"

describe("WorkflowCompareCard", () => {
  it("renders an empty state when fewer than two workflows are available", () => {
    render(
      <WorkflowCompareCard
        workflowCosts={[
          {
            dimension: "workflow_archetype",
            label: "debugging",
            session_count: 2,
            total_estimated_cost: 12.5,
            avg_cost_per_session: 6.25,
            cost_per_successful_outcome: 12.5,
          },
        ]}
        qualityRows={[]}
      />,
    )

    expect(screen.getByText("Need at least two workflows with cost data to compare them.")).toBeInTheDocument()
  })

  it("compares workflow metrics and allows dimension switching", () => {
    render(
      <WorkflowCompareCard
        workflowCosts={[
          {
            dimension: "workflow_archetype",
            label: "debugging",
            session_count: 2,
            total_estimated_cost: 12.5,
            avg_cost_per_session: 6.25,
            cost_per_successful_outcome: 12.5,
          },
          {
            dimension: "workflow_archetype",
            label: "refactor",
            session_count: 3,
            total_estimated_cost: 9.0,
            avg_cost_per_session: 3,
            cost_per_successful_outcome: 4.5,
          },
          {
            dimension: "workflow_fingerprint",
            label: "bug fix: read -> edit -> ship",
            session_count: 1,
            total_estimated_cost: 4.2,
            avg_cost_per_session: 4.2,
            cost_per_successful_outcome: 4.2,
          },
          {
            dimension: "workflow_fingerprint",
            label: "refactor: search -> read -> edit -> ship",
            session_count: 2,
            total_estimated_cost: 5.3,
            avg_cost_per_session: 2.65,
            cost_per_successful_outcome: null,
          },
        ]}
        qualityRows={[
          {
            dimension: "workflow_archetype",
            label: "debugging",
            linked_sessions: 2,
            linked_prs: 2,
            merge_rate: 1,
            avg_review_comments_per_pr: 1.5,
            avg_findings_per_pr: 0.5,
            high_severity_findings_per_pr: 0,
            avg_time_to_merge_hours: 4,
            findings_fix_rate: 1,
          },
          {
            dimension: "workflow_archetype",
            label: "refactor",
            linked_sessions: 3,
            linked_prs: 1,
            merge_rate: 0.5,
            avg_review_comments_per_pr: 2,
            avg_findings_per_pr: 1,
            high_severity_findings_per_pr: 0.5,
            avg_time_to_merge_hours: 6,
            findings_fix_rate: 0.5,
          },
          {
            dimension: "workflow_fingerprint",
            label: "bug fix: read -> edit -> ship",
            linked_sessions: 1,
            linked_prs: 1,
            merge_rate: 1,
            avg_review_comments_per_pr: 1,
            avg_findings_per_pr: 0,
            high_severity_findings_per_pr: 0,
            avg_time_to_merge_hours: 3,
            findings_fix_rate: null,
          },
        ]}
      />,
    )

    expect(screen.getByText("Workflow Archetype")).toBeInTheDocument()
    expect(screen.getAllByText("Debugging").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Refactor").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("$12.50").length).toBeGreaterThanOrEqual(1)

    fireEvent.change(screen.getByLabelText("Dimension"), {
      target: { value: "workflow_fingerprint" },
    })

    expect(screen.getByText("Workflow Fingerprint")).toBeInTheDocument()
    expect(screen.getAllByText("bug fix: read -> edit -> ship").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("refactor: search -> read -> edit -> ship").length).toBeGreaterThanOrEqual(1)
  })
})
