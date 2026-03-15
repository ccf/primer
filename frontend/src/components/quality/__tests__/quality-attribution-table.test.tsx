import { render, screen } from "@testing-library/react"

import { QualityAttributionTable } from "@/components/quality/quality-attribution-table"

describe("QualityAttributionTable", () => {
  it("renders an empty state when no rows are available", () => {
    render(<QualityAttributionTable rows={[]} />)

    expect(screen.getByText("No attributed PR outcomes yet.")).toBeInTheDocument()
  })

  it("groups attribution rows by behavior dimension", () => {
    render(
      <QualityAttributionTable
        rows={[
          {
            dimension: "session_type",
            label: "bug_fix",
            linked_sessions: 3,
            linked_prs: 2,
            merge_rate: 1,
            avg_review_comments_per_pr: 1.5,
            avg_findings_per_pr: 0.5,
            high_severity_findings_per_pr: 0,
            avg_time_to_merge_hours: 4,
            findings_fix_rate: 1,
          },
          {
            dimension: "agent_type",
            label: "codex_cli",
            linked_sessions: 2,
            linked_prs: 2,
            merge_rate: 0.5,
            avg_review_comments_per_pr: 2,
            avg_findings_per_pr: 1,
            high_severity_findings_per_pr: 0.5,
            avg_time_to_merge_hours: 6,
            findings_fix_rate: 0.5,
          },
          {
            dimension: "workflow_archetype",
            label: "debugging",
            linked_sessions: 1,
            linked_prs: 1,
            merge_rate: 1,
            avg_review_comments_per_pr: 1,
            avg_findings_per_pr: 0,
            high_severity_findings_per_pr: 0,
            avg_time_to_merge_hours: 2,
            findings_fix_rate: null,
          },
        ]}
      />,
    )

    expect(screen.getByText("Session Type")).toBeInTheDocument()
    expect(screen.getByText("Agent Type")).toBeInTheDocument()
    expect(screen.getByText("Workflow Archetype")).toBeInTheDocument()
    expect(screen.getByText("Bug Fix")).toBeInTheDocument()
    expect(screen.getByText("Codex Cli")).toBeInTheDocument()
    expect(screen.getByText("Debugging")).toBeInTheDocument()
    expect(screen.getAllByText("100%").length).toBeGreaterThanOrEqual(2)
    expect(screen.getAllByText("50%").length).toBeGreaterThanOrEqual(2)
  })
})
