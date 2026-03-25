import { fireEvent, render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/hooks/use-api-queries", () => ({
  useTeams: vi.fn(),
  useEngineers: vi.fn(),
  useProjectAnalytics: vi.fn(),
  useCompareAnalytics: vi.fn(),
}))

import {
  useCompareAnalytics,
  useEngineers,
  useProjectAnalytics,
  useTeams,
} from "@/hooks/use-api-queries"
import { ComparePage } from "../compare"

const mockUseTeams = vi.mocked(useTeams)
const mockUseEngineers = vi.mocked(useEngineers)
const mockUseProjectAnalytics = vi.mocked(useProjectAnalytics)
const mockUseCompareAnalytics = vi.mocked(useCompareAnalytics)

describe("ComparePage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseTeams.mockReturnValue({
      data: [
        { id: "team-1", name: "Alpha" },
        { id: "team-2", name: "Beta" },
      ],
      isLoading: false,
    } as never)
    mockUseEngineers.mockReturnValue({
      data: [
        { id: "eng-1", name: "Alice", display_name: "Alice", team_id: "team-1" },
        { id: "eng-2", name: "Bob", display_name: "Bob", team_id: "team-2" },
      ],
      isLoading: false,
    } as never)
    mockUseProjectAnalytics.mockReturnValue({
      data: {
        total_count: 2,
        projects: [
          { project_name: "alpha-app" },
          { project_name: "beta-app" },
        ],
      },
      isLoading: false,
    } as never)
    mockUseCompareAnalytics.mockReturnValue({
      data: {
        mode: "team",
        left: {
          label: "Alpha",
          total_sessions: 12,
          success_rate: 0.75,
          total_cost: 12.4,
          avg_cost_per_session: 1.03,
          cost_per_successful_outcome: 1.4,
          pr_merge_rate: 0.8,
          findings_fix_rate: 0.7,
          effectiveness_score: 82.1,
          leverage_score: 74.6,
          top_workflows: [
            { label: "debugging", session_count: 5, share_of_sessions: 0.42 },
          ],
        },
        right: {
          label: "Beta",
          total_sessions: 8,
          success_rate: 0.5,
          total_cost: 10.4,
          avg_cost_per_session: 1.3,
          cost_per_successful_outcome: 2.1,
          pr_merge_rate: 0.55,
          findings_fix_rate: 0.5,
          effectiveness_score: 61.4,
          leverage_score: 58.2,
          top_workflows: [
            { label: "implementation", session_count: 3, share_of_sessions: 0.38 },
          ],
        },
        delta: {
          total_sessions: 4,
          success_rate: 0.25,
          total_cost: 2.0,
          avg_cost_per_session: -0.27,
          cost_per_successful_outcome: -0.7,
          pr_merge_rate: 0.25,
          findings_fix_rate: 0.2,
          effectiveness_score: 20.7,
          leverage_score: 16.4,
        },
      },
      isLoading: false,
    } as never)
  })

  it("renders compare mode snapshots and supports switching modes", () => {
    render(<ComparePage teamId={null} dateRange={null} />)

    expect(screen.getByText("Compare")).toBeInTheDocument()
    expect(
      screen.queryByText("Selected period vs previous period"),
    ).not.toBeInTheDocument()
    expect(screen.getAllByText("Alpha").length).toBeGreaterThan(0)
    expect(screen.getAllByText("Beta").length).toBeGreaterThan(0)
    expect(screen.getAllByText("Top Workflows").length).toBeGreaterThan(0)

    fireEvent.click(screen.getByRole("button", { name: "Periods" }))
    expect(screen.getByText("Selected period vs previous period")).toBeInTheDocument()
  })
})
