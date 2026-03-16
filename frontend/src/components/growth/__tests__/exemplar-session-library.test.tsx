import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"

import { ExemplarSessionLibrary } from "@/components/growth/exemplar-session-library"

describe("ExemplarSessionLibrary", () => {
  it("renders an empty state", () => {
    render(
      <MemoryRouter>
        <ExemplarSessionLibrary exemplars={[]} />
      </MemoryRouter>,
    )

    expect(screen.getByText("No exemplar sessions identified yet.")).toBeInTheDocument()
  })

  it("renders workflow-aware exemplar cards", () => {
    render(
      <MemoryRouter>
        <ExemplarSessionLibrary
          exemplars={[
            {
              exemplar_id: "exemplar:sess-1",
              title: "debugging: read -> edit -> execute -> fix",
              summary: "Backed by 3 engineers across 4 sessions.",
              why_selected: "Chosen as the fastest successful example for debugging on primer.",
              session_id: "sess-1",
              engineer_id: "eng-1",
              engineer_name: "Alice Example",
              project_name: "primer",
              outcome: "success",
              helpfulness: "very_helpful",
              session_summary: "Resolved the failing auth flow after reproducing locally.",
              duration_seconds: 180,
              estimated_cost: 1.24,
              tools_used: ["Read", "Edit", "Bash"],
              workflow_archetype: "debugging",
              workflow_fingerprint: "debugging: read -> edit -> execute -> fix",
              workflow_steps: ["read", "edit", "execute", "fix"],
              supporting_session_count: 4,
              supporting_engineer_count: 3,
              supporting_pattern_count: 2,
              success_rate: 1,
              linked_patterns: [
                {
                  cluster_id: "cluster-1",
                  cluster_type: "session_type",
                  cluster_label: "debugging on primer",
                  session_count: 4,
                  engineer_count: 3,
                  success_rate: 1,
                },
              ],
            },
          ]}
        />
      </MemoryRouter>,
    )

    expect(screen.getAllByText("debugging: read -> edit -> execute -> fix")).toHaveLength(2)
    expect(screen.getByText("Why This Exemplar")).toBeInTheDocument()
    expect(screen.getByText("Workflow Evidence")).toBeInTheDocument()
    expect(screen.getByText("$1.24")).toBeInTheDocument()
    expect(screen.getByText("debugging on primer")).toBeInTheDocument()
    expect(screen.getByText("Open exemplar")).toHaveAttribute("href", "/sessions/sess-1")
  })
})
