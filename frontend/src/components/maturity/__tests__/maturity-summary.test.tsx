import { render, screen } from "@testing-library/react"

import { MaturitySummary } from "@/components/maturity/maturity-summary"

describe("MaturitySummary", () => {
  it("renders the model diversity summary card", () => {
    render(
      <MaturitySummary
        data={{
          avg_leverage_score: 74.2,
          avg_effectiveness_score: 81.1,
          orchestration_adoption_rate: 0.42,
          team_orchestration_adoption_rate: 0.35,
          explicit_customization_adoption_rate: 0.61,
          model_diversity_avg: 0.48,
          sessions_analyzed: 128,
          tool_categories: { core: {}, search: {}, orchestration: {}, skill: {}, mcp: {} },
          engineer_profiles: [],
          daily_leverage: [],
          agent_skill_breakdown: [],
          customization_breakdown: [],
          high_performer_stacks: [],
          team_customization_landscape: [],
          customization_state_funnel: [],
          toolchain_reliability: [],
          harness_configuration_fingerprints: [],
          delegation_patterns: [],
          agent_team_modes: [],
          customization_outcomes: [],
          project_readiness: [],
          context_quality: [],
        }}
      />,
    )

    expect(screen.getByText("Avg Model Diversity")).toBeInTheDocument()
    expect(screen.getByText("48%")).toBeInTheDocument()
  })
})
