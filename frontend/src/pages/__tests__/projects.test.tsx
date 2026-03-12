import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"

vi.mock("@/hooks/use-api-queries", () => ({
  useProjectAnalytics: vi.fn(),
  useProjectComparison: vi.fn(),
}))

import { useProjectAnalytics, useProjectComparison } from "@/hooks/use-api-queries"
import { ProjectsPage } from "../projects"

const mockUseProjectAnalytics = vi.mocked(useProjectAnalytics)
const mockUseProjectComparison = vi.mocked(useProjectComparison)

describe("ProjectsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseProjectAnalytics.mockReturnValue({
      data: undefined,
      isLoading: false,
    } as ReturnType<typeof useProjectAnalytics>)
    mockUseProjectComparison.mockReturnValue({
      data: undefined,
      isLoading: false,
    } as ReturnType<typeof useProjectComparison>)
  })

  it("renders the cross-project comparison panel when comparison data is available", () => {
    mockUseProjectAnalytics.mockReturnValue({
      data: {
        total_count: 2,
        projects: [
          {
            project_name: "primer",
            total_sessions: 8,
            unique_engineers: 3,
            total_tokens: 20000,
            estimated_cost: 12.5,
            outcome_distribution: { success: 6, failure: 2 },
            top_tools: ["Edit", "Bash"],
          },
          {
            project_name: "legacy-app",
            total_sessions: 5,
            unique_engineers: 2,
            total_tokens: 12000,
            estimated_cost: 8.25,
            outcome_distribution: { success: 2, failure: 3 },
            top_tools: ["Read", "Grep"],
          },
        ],
      },
      isLoading: false,
    } as unknown as ReturnType<typeof useProjectAnalytics>)
    mockUseProjectComparison.mockReturnValue({
      data: {
        compared_projects: 2,
        easiest_projects: [
          {
            project_name: "primer",
            total_sessions: 8,
            unique_engineers: 3,
            effectiveness_score: 82.4,
            effectiveness_rate: 0.75,
            quality_rate: 1,
            friction_rate: 0.25,
            avg_cost_per_session: 1.56,
            measurement_confidence: 1,
            ai_readiness_score: 88,
            dominant_agent_type: "claude_code",
            top_recommendation_title: "Turn the best workflow into a project playbook",
          },
        ],
        hardest_projects: [
          {
            project_name: "legacy-app",
            total_sessions: 5,
            unique_engineers: 2,
            effectiveness_score: 41.2,
            effectiveness_rate: 0.4,
            quality_rate: 0.5,
            friction_rate: 0.6,
            avg_cost_per_session: 2.12,
            measurement_confidence: 0.83,
            ai_readiness_score: 35,
            dominant_agent_type: "cursor",
            top_recommendation_title: "Codify project context for agents",
          },
        ],
      },
      isLoading: false,
    } as unknown as ReturnType<typeof useProjectComparison>)

    render(
      <MemoryRouter>
        <ProjectsPage teamId={null} dateRange={null} />
      </MemoryRouter>,
    )

    expect(screen.getByText("Cross-Project Comparison")).toBeInTheDocument()
    expect(screen.getAllByText("Best AI Fit").length).toBeGreaterThan(0)
    expect(screen.getAllByText("Needs Enablement").length).toBeGreaterThan(0)
    expect(screen.getAllByText("primer").length).toBeGreaterThan(0)
    expect(screen.getAllByText("legacy-app").length).toBeGreaterThan(0)
    expect(screen.getByText("Turn the best workflow into a project playbook")).toBeInTheDocument()
  })
})
