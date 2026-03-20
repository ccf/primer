import { render, screen } from "@testing-library/react"

import { PromptOpportunityCards } from "@/components/growth/prompt-opportunity-cards"

describe("PromptOpportunityCards", () => {
  it("renders an empty state", () => {
    render(<PromptOpportunityCards patterns={[]} />)

    expect(screen.getByText("No high-value prompt opportunities identified yet.")).toBeInTheDocument()
  })

  it("renders underused prompt opportunities", () => {
    render(
      <PromptOpportunityCards
        patterns={[
          {
            prompt_pattern_id: "abc123",
            prompt_preview: "Generate a concise release checklist for this repo",
            normalized_prompt: "generate a concise release checklist for this repo",
            engineer_count: 1,
            session_count: 2,
            adoption_rate: 0.25,
            success_rate: 1,
            avg_session_cost: 0.09,
            cost_per_successful_outcome: 0.09,
            primary_workflow_archetype: "docs",
            workflow_archetypes: ["docs"],
            top_projects: ["primer"],
          },
        ]}
      />,
    )

    expect(screen.getByText("Generate a concise release checklist for this repo")).toBeInTheDocument()
    expect(screen.getByText("25%")).toBeInTheDocument()
    expect(screen.getByText("100%")).toBeInTheDocument()
    expect(screen.getByText("$0.09")).toBeInTheDocument()
    expect(screen.getByText("Docs")).toBeInTheDocument()
  })
})
