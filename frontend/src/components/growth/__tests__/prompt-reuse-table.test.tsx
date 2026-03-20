import { render, screen } from "@testing-library/react"

import { PromptReuseTable } from "@/components/growth/prompt-reuse-table"

describe("PromptReuseTable", () => {
  it("renders an empty state", () => {
    render(<PromptReuseTable patterns={[]} />)

    expect(screen.getByText("No reusable prompt patterns detected yet.")).toBeInTheDocument()
  })

  it("renders prompt reuse patterns", () => {
    render(
      <PromptReuseTable
        patterns={[
          {
            prompt_pattern_id: "abc123",
            prompt_preview: "Fix the auth bug for tenant 123",
            normalized_prompt: "fix the auth bug for tenant <id>",
            engineer_count: 2,
            session_count: 3,
            adoption_rate: 0.5,
            success_rate: 1,
            avg_session_cost: 0.11,
            cost_per_successful_outcome: 0.11,
            primary_workflow_archetype: "debugging",
            workflow_archetypes: ["debugging"],
            top_projects: ["primer"],
          },
        ]}
      />,
    )

    expect(screen.getByText("Fix the auth bug for tenant 123")).toBeInTheDocument()
    expect(screen.getByText("fix the auth bug for tenant <id>")).toBeInTheDocument()
    expect(screen.getByText("50%")).toBeInTheDocument()
    expect(screen.getByText("100%")).toBeInTheDocument()
    expect(screen.getByText("$0.11")).toBeInTheDocument()
    expect(screen.getByText("Debugging")).toBeInTheDocument()
  })
})
