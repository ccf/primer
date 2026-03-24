import { render, screen } from "@testing-library/react"

import { PersonalImpactReview } from "@/components/insights/personal-impact-review"

describe("PersonalImpactReview", () => {
  it("renders the empty state when no review is available", () => {
    render(
      <PersonalImpactReview
        profile={{
          engineer_id: "eng-1",
          name: "Alice Example",
          email: "alice@example.com",
          display_name: "Alice Example",
          team_id: null,
          team_name: null,
          avatar_url: null,
          github_username: null,
          created_at: "2026-03-01T00:00:00Z",
          overview: {
            total_sessions: 0,
            total_engineers: 1,
            total_messages: 0,
            total_tool_calls: 0,
            total_input_tokens: 0,
            total_output_tokens: 0,
            estimated_cost: 0,
            avg_session_duration: null,
            avg_messages_per_session: 0,
            outcome_counts: {},
            session_type_counts: {},
            success_rate: null,
            previous_period: null,
            end_reason_counts: {},
            cache_hit_rate: null,
            avg_health_score: null,
            agent_type_counts: {},
          },
          weekly_trajectory: [],
          friction: [],
          config_suggestions: [],
          strengths: {
            engineer_profiles: [],
            team_skill_gaps: [],
            reusable_assets: [],
            underused_reusable_assets: [],
            prompt_patterns: [],
            underused_prompt_patterns: [],
            total_engineers: 0,
            total_session_types: 0,
            total_tools_used: 0,
          },
          learning_paths: [],
          tool_recommendations: [],
          model_recommendations: [],
          quality: {},
          leverage_score: null,
          effectiveness: null,
          impact_review: null,
          projects: [],
          tool_rankings: [],
          workflow_playbooks: [],
        }}
      />,
    )

    expect(screen.getByText("No impact review is available yet.")).toBeInTheDocument()
  })

  it("renders the impact review narrative, workflows, and next step", () => {
    render(
      <PersonalImpactReview
        profile={{
          engineer_id: "eng-1",
          name: "Alice Example",
          email: "alice@example.com",
          display_name: "Alice Example",
          team_id: null,
          team_name: "Primer Team",
          avatar_url: null,
          github_username: null,
          created_at: "2026-03-01T00:00:00Z",
          overview: {
            total_sessions: 12,
            total_engineers: 1,
            total_messages: 48,
            total_tool_calls: 20,
            total_input_tokens: 1000,
            total_output_tokens: 500,
            estimated_cost: 14.2,
            avg_session_duration: 420,
            avg_messages_per_session: 4,
            outcome_counts: {},
            session_type_counts: {},
            success_rate: 0.75,
            previous_period: null,
            end_reason_counts: {},
            cache_hit_rate: null,
            avg_health_score: null,
            agent_type_counts: {},
          },
          weekly_trajectory: [],
          friction: [],
          config_suggestions: [],
          strengths: {
            engineer_profiles: [],
            team_skill_gaps: [],
            reusable_assets: [],
            underused_reusable_assets: [],
            prompt_patterns: [],
            underused_prompt_patterns: [],
            total_engineers: 0,
            total_session_types: 0,
            total_tools_used: 0,
          },
          learning_paths: [],
          tool_recommendations: [],
          model_recommendations: [],
          quality: {},
          leverage_score: 72.4,
          effectiveness: {
            score: 81.6,
            breakdown: {
              success_rate: 0.75,
              cost_efficiency: 0.8,
              quality_outcomes: 0.9,
              follow_through: 0.85,
            },
            cost_per_successful_outcome: 18.9,
            benchmark_cost_per_successful_outcome: 20.4,
          },
          impact_review: {
            headline: "High-impact momentum with strong workflow discipline",
            summary: "Alice Example logged 12 sessions in this period, 75% ended successfully.",
            workflow_maturity_label: "advancing",
            trajectory_signal: "improving",
            strengths: ["Consistently converts sessions into successful outcomes."],
            focus_areas: ["Lower cost per successful outcome by tightening workflows or model choice."],
            top_workflows: [
              {
                archetype: "debugging",
                session_count: 5,
                share_of_sessions: 0.417,
                success_rate: 0.8,
                avg_duration_seconds: 390,
              },
            ],
            next_step_title: "Use claude-sonnet-4-5-20250929 for debugging work",
            next_step_description: "Peers handling debugging sessions succeed with it at lower cost.",
          },
          projects: ["primer"],
          tool_rankings: [],
          workflow_playbooks: [],
        }}
      />,
    )

    expect(screen.getByText("High-impact momentum with strong workflow discipline")).toBeInTheDocument()
    expect(screen.getByText("Top Workflows")).toBeInTheDocument()
    expect(screen.getByText("Debugging")).toBeInTheDocument()
    expect(screen.getByText("Recommended Next Move")).toBeInTheDocument()
    expect(screen.getByText("Use claude-sonnet-4-5-20250929 for debugging work")).toBeInTheDocument()
    expect(screen.getByText("What's Working")).toBeInTheDocument()
    expect(screen.getByText("Focus Next")).toBeInTheDocument()
  })
})
