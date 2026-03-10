import { render, screen } from "@testing-library/react"

import { ProjectWorkflowSection } from "@/components/projects/project-workflow-section"

describe("ProjectWorkflowSection", () => {
  it("renders workflow fingerprints and friction hotspots", () => {
    render(
      <ProjectWorkflowSection
        workflowSummary={{
          fingerprinted_sessions: 5,
          total_sessions: 6,
          coverage_pct: 0.833,
          fingerprints: [
            {
              fingerprint_id: "implementation::search+read+edit+execute",
              label: "implementation: search -> read -> edit -> execute",
              session_type: "implementation",
              steps: ["search", "read", "edit", "execute"],
              session_count: 3,
              share_of_sessions: 0.5,
              success_rate: 0.667,
              avg_duration_seconds: 2400,
              top_tools: ["Grep", "Read", "Edit"],
              top_friction_types: ["context_switching"],
            },
          ],
          friction_hotspots: [
            {
              friction_type: "context_switching",
              session_count: 2,
              share_of_sessions: 0.333,
              total_occurrences: 3,
              impact_score: 0.25,
              linked_fingerprints: ["implementation: search -> read -> edit -> execute"],
              sample_details: ["Needed to switch across multiple files and branches."],
            },
          ],
        }}
      />,
    )

    expect(screen.getByText("Workflow Fingerprints")).toBeInTheDocument()
    expect(screen.getByText("83%")).toBeInTheDocument()
    expect(
      screen.getAllByText("implementation: search -> read -> edit -> execute"),
    ).toHaveLength(2)
    expect(screen.getByText("Success 67%")).toBeInTheDocument()
    expect(screen.getByText("Grep")).toBeInTheDocument()
    expect(screen.getByText("Friction Hotspots")).toBeInTheDocument()
    expect(screen.getAllByText("context switching")).toHaveLength(2)
    expect(screen.getByText("Success penalty 25%")).toBeInTheDocument()
    expect(screen.getByText("Needed to switch across multiple files and branches.")).toBeInTheDocument()
  })
})
