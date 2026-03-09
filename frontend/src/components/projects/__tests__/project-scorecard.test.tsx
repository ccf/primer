import { render, screen } from "@testing-library/react"

import { ProjectScorecard } from "@/components/projects/project-scorecard"

describe("ProjectScorecard", () => {
  it("renders scorecard metrics and fallbacks", () => {
    render(
      <ProjectScorecard
        scorecard={{
          adoption_rate: 0.75,
          effectiveness_rate: 0.5,
          quality_rate: 1,
          avg_cost_per_session: 2.5,
          cost_per_successful_outcome: null,
          measurement_confidence: 0.9,
        }}
        overview={{
          total_sessions: 12,
          total_engineers: 4,
          total_messages: 0,
          total_tool_calls: 0,
          total_input_tokens: 0,
          total_output_tokens: 0,
          estimated_cost: 10,
          avg_session_duration: null,
          avg_messages_per_session: null,
          outcome_counts: {},
          session_type_counts: {},
          success_rate: 0.5,
          previous_period: null,
          end_reason_counts: {},
          cache_hit_rate: null,
          avg_health_score: null,
          agent_type_counts: {},
        }}
      />,
    )

    expect(screen.getByText("Adoption")).toBeInTheDocument()
    expect(screen.getByText("75%")).toBeInTheDocument()
    expect(screen.getByText("4 engineers active on this project")).toBeInTheDocument()
    expect(screen.getByText("50%")).toBeInTheDocument()
    expect(screen.getByText("$2.50")).toBeInTheDocument()
    expect(screen.getByText("Average cost per session")).toBeInTheDocument()
    expect(screen.getByText("90%")).toBeInTheDocument()
  })
})
