import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"

import { LearningPathCards } from "@/components/growth/learning-path-cards"

describe("LearningPathCards", () => {
  it("renders an empty state", () => {
    render(
      <MemoryRouter>
        <LearningPathCards paths={[]} />
      </MemoryRouter>,
    )

    expect(screen.getByText("No learning paths available.")).toBeInTheDocument()
  })

  it("renders exemplar study links for recommendations", () => {
    render(
      <MemoryRouter>
        <LearningPathCards
          paths={[
            {
              engineer_id: "eng-1",
              name: "Alice Example",
              total_sessions: 4,
              coverage_score: 0.5,
              complexity_trend: "flat",
              recommendations: [
                {
                  category: "tool_gap",
                  skill_area: "Edit",
                  title: "Learn the Edit tool",
                  description: "2/3 teammates use Edit, but you haven't used it yet.",
                  priority: "high",
                  evidence: {},
                  exemplars: [
                    {
                      session_id: "sess-1",
                      title: "debugging: read -> edit -> execute -> fix",
                      engineer_name: "Bob Example",
                      project_name: "primer",
                      summary: "Resolved an auth regression.",
                      relevance_reason: "Shows Edit in a successful peer workflow.",
                      workflow_archetype: "debugging",
                      workflow_fingerprint: "debugging: read -> edit -> execute -> fix",
                      duration_seconds: 75,
                      estimated_cost: 0.5,
                      tools_used: ["Read", "Edit", "Bash"],
                    },
                  ],
                },
              ],
            },
          ]}
        />
      </MemoryRouter>,
    )

    expect(screen.getByText("Study Exemplars")).toBeInTheDocument()
    expect(screen.getByText("Bob Example • primer")).toBeInTheDocument()
    expect(screen.getByText("Shows Edit in a successful peer workflow.")).toBeInTheDocument()
    expect(screen.getByText("Debugging")).toBeInTheDocument()
    expect(screen.getByRole("link")).toHaveAttribute("href", "/sessions/sess-1")
  })
})
