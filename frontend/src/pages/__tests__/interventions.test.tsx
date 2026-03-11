import { beforeEach, describe, expect, it, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("@/lib/auth-context", () => ({
  useAuth: vi.fn(() => ({
    user: {
      engineer_id: "lead-1",
      name: "Lead",
      email: "lead@example.com",
      role: "team_lead",
      team_id: "team-1",
      avatar_url: null,
      github_username: null,
      display_name: null,
    },
  })),
}))

vi.mock("@/hooks/use-api-queries", () => ({
  useInterventions: vi.fn(),
  useInterventionEffectiveness: vi.fn(),
  useEngineers: vi.fn(),
}))

vi.mock("@/hooks/use-api-mutations", () => ({
  useCreateIntervention: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useUpdateIntervention: vi.fn(() => ({ mutate: vi.fn() })),
}))

import {
  useInterventionEffectiveness,
  useInterventions,
  useEngineers,
} from "@/hooks/use-api-queries"
import { InterventionsPage } from "../interventions"

const mockUseInterventions = vi.mocked(useInterventions)
const mockUseInterventionEffectiveness = vi.mocked(useInterventionEffectiveness)
const mockUseEngineers = vi.mocked(useEngineers)

describe("InterventionsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseEngineers.mockReturnValue({
      data: [
        {
          id: "lead-1",
          name: "Lead",
          email: "lead@example.com",
          team_id: "team-1",
          role: "team_lead",
          avatar_url: null,
          github_username: null,
          display_name: null,
          is_active: true,
          created_at: "2026-03-01T00:00:00Z",
        },
      ],
      isLoading: false,
    } as unknown as ReturnType<typeof useEngineers>)
    mockUseInterventionEffectiveness.mockReturnValue({
      data: {
        summary: {
          total_interventions: 1,
          completed_interventions: 1,
          measured_interventions: 1,
          improved_interventions: 1,
          improvement_rate: 1,
          avg_completion_days: 3.5,
          avg_success_rate_delta: 0.2,
          avg_friction_delta: 2,
          avg_findings_per_pr_delta: 0.5,
          avg_cost_per_session_delta: -0.3,
        },
        by_team: [
          {
            key: "team-1",
            label: "Team One",
            completed_interventions: 1,
            measured_interventions: 1,
            improved_interventions: 1,
            improvement_rate: 1,
            avg_completion_days: 3.5,
            avg_success_rate_delta: 0.2,
            avg_friction_delta: 2,
            avg_findings_per_pr_delta: 0.5,
            avg_cost_per_session_delta: -0.3,
          },
        ],
        by_project: [],
        by_engineer_cohort: [],
      },
      isLoading: false,
    } as unknown as ReturnType<typeof useInterventionEffectiveness>)
  })

  it("renders intervention counts and cards", () => {
    mockUseInterventions.mockReturnValue({
      data: [
        {
          id: "int-1",
          team_id: "team-1",
          team_name: "Team One",
          engineer_id: null,
          engineer: null,
          owner_engineer_id: "lead-1",
          owner_engineer: { id: "lead-1", name: "Lead", email: "lead@example.com" },
          created_by_engineer_id: "lead-1",
          project_name: "primer",
          category: "workflow",
          severity: "warning",
          status: "planned",
          title: "Reduce triage churn",
          description: "Track a structured pre-implementation checklist.",
          due_date: null,
          completed_at: null,
          source_type: "recommendation",
          source_title: "Recurring friction: context_switching",
          evidence: { count: 5 },
          baseline_start_at: "2026-02-01T00:00:00Z",
          baseline_end_at: "2026-03-01T00:00:00Z",
          baseline_metrics: {
            window_start: "2026-02-01T00:00:00Z",
            window_end: "2026-03-01T00:00:00Z",
            total_sessions: 12,
            success_rate: 0.5,
            avg_cost_per_session: 1.2,
            cost_per_successful_outcome: 2.4,
            friction_events: 8,
            total_prs: 2,
            findings_per_pr: 1.5,
          },
          current_metrics: {
            window_start: "2026-02-08T00:00:00Z",
            window_end: "2026-03-08T00:00:00Z",
            total_sessions: 14,
            success_rate: 0.6,
            avg_cost_per_session: 1.1,
            cost_per_successful_outcome: 2.0,
            friction_events: 5,
            total_prs: 3,
            findings_per_pr: 1.0,
          },
          created_at: "2026-03-01T00:00:00Z",
          updated_at: "2026-03-08T00:00:00Z",
        },
      ],
      isLoading: false,
    } as unknown as ReturnType<typeof useInterventions>)

    render(<InterventionsPage teamId="team-1" />)

    expect(screen.getByText("Interventions")).toBeInTheDocument()
    expect(screen.getByText("Effectiveness")).toBeInTheDocument()
    expect(screen.getByText("Reduce triage churn")).toBeInTheDocument()
    expect(screen.getAllByText("Planned").length).toBeGreaterThan(0)
    expect(screen.getByText("Tracked follow-through for recommendations, coaching, and workflow changes")).toBeInTheDocument()
    expect(screen.getByText(/Recurring friction/)).toBeInTheDocument()
    expect(screen.getByText("By Team")).toBeInTheDocument()
    expect(screen.getByText("Team One")).toBeInTheDocument()
    expect(screen.getByText("-$0.30")).toBeInTheDocument()
  })

  it("shows empty state when there are no interventions", () => {
    mockUseInterventions.mockReturnValue({
      data: [],
      isLoading: false,
    } as unknown as ReturnType<typeof useInterventions>)

    render(<InterventionsPage teamId="team-1" />)

    expect(
      screen.getByText(/No interventions yet. Create one from a recommendation/i),
    ).toBeInTheDocument()
  })
})
