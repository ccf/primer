import { render, screen } from "@testing-library/react"

import { ModelRecommendationList } from "@/components/insights/model-recommendation-list"

describe("ModelRecommendationList", () => {
  it("renders an empty state", () => {
    render(<ModelRecommendationList recommendations={[]} />)

    expect(screen.getByText("No model recommendations available yet.")).toBeInTheDocument()
  })

  it("renders model recommendations", () => {
    render(
      <ModelRecommendationList
        recommendations={[
          {
            current_model: "claude-opus-4",
            recommended_model: "claude-sonnet-4-5-20250929",
            recommendation_type: "downshift",
            workflow_archetype: "debugging",
            title: "Use claude-sonnet-4-5-20250929 for debugging work",
            description: "Peers handling debugging sessions succeed with this model at lower cost.",
            priority: "high",
            current_success_rate: 1,
            recommended_success_rate: 1,
            current_avg_cost: 0.75,
            recommended_avg_cost: 0.18,
            supporting_session_count: 4,
            supporting_engineer_count: 2,
          },
        ]}
      />,
    )

    expect(screen.getByText("Use claude-sonnet-4-5-20250929 for debugging work")).toBeInTheDocument()
    expect(screen.getByText("Downshift")).toBeInTheDocument()
    expect(screen.getByText("Debugging")).toBeInTheDocument()
    expect(screen.getByText("claude-opus-4")).toBeInTheDocument()
    expect(screen.getByText("claude-sonnet-4-5-20250929")).toBeInTheDocument()
    expect(screen.getByText("100% -> 100%")).toBeInTheDocument()
    expect(screen.getByText(/\$0\.75/)).toBeInTheDocument()
    expect(screen.getByText(/\$0\.18/)).toBeInTheDocument()
  })
})
