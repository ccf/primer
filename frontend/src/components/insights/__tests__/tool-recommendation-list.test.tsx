import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"

import { ToolRecommendationList } from "@/components/insights/tool-recommendation-list"

describe("ToolRecommendationList", () => {
  it("renders an empty state", () => {
    render(
      <MemoryRouter>
        <ToolRecommendationList recommendations={[]} />
      </MemoryRouter>,
    )

    expect(screen.getByText("No tool recommendations available yet.")).toBeInTheDocument()
  })

  it("renders recommendation evidence and exemplar links", () => {
    render(
      <MemoryRouter>
        <ToolRecommendationList
          recommendations={[
            {
              tool_name: "Grep",
              title: "Try Grep",
              description:
                "Peers repeatedly use Grep in successful debugging workflows on primer.",
              priority: "high",
              related_skill_areas: ["debugging"],
              related_categories: ["session_type_gap"],
              matching_projects: ["primer"],
              supporting_exemplar_count: 2,
              project_context_match_count: 1,
              exemplar: {
                session_id: "sess-1",
                title: "debugging: read -> grep -> edit -> fix",
                engineer_name: "Bob Example",
                project_name: "primer",
                summary: "Tracked down the failing auth route.",
                relevance_reason: "Strong peer example of a 'debugging' workflow.",
                workflow_archetype: "debugging",
                workflow_fingerprint: "debugging: read -> grep -> edit -> fix",
                duration_seconds: 120,
                estimated_cost: 0.35,
                tools_used: ["Read", "Grep", "Edit"],
              },
            },
          ]}
        />
      </MemoryRouter>,
    )

    expect(screen.getByText("Try Grep")).toBeInTheDocument()
    expect(screen.getByText("Debugging")).toBeInTheDocument()
    expect(screen.getByText("primer")).toBeInTheDocument()
    expect(screen.getByText("Best Exemplar")).toBeInTheDocument()
    expect(screen.getByRole("link")).toHaveAttribute("href", "/sessions/sess-1")
  })
})
