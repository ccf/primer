import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { AdminPerformanceTab } from "../admin-performance-tab"

const mockUseProductivity = vi.fn()
const mockUseQualityMetrics = vi.fn()
const mockUseCostAnalytics = vi.fn()
const mockUseMaturityAnalytics = vi.fn()

vi.mock("@/hooks/use-api-queries", () => ({
  useProductivity: () => mockUseProductivity(),
  useQualityMetrics: () => mockUseQualityMetrics(),
  useCostAnalytics: () => mockUseCostAnalytics(),
  useMaturityAnalytics: () => mockUseMaturityAnalytics(),
}))

describe("AdminPerformanceTab", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseProductivity.mockReturnValue({
      data: {
        sessions_per_engineer_per_day: 1.8,
        avg_cost_per_session: 1.2,
        cost_per_successful_outcome: 2.4,
        estimated_time_saved_hours: 12,
        estimated_value_created: 1200,
        adoption_rate: 72.0,
        power_users: 4,
        total_engineers_in_scope: 9,
        total_cost: 18.4,
        roi_ratio: 2.1,
      },
      isLoading: false,
    })
    mockUseQualityMetrics.mockReturnValue({
      data: {
        overview: {
          total_prs: 7,
          pr_merge_rate: 0.86,
          avg_time_to_merge_hours: 9.5,
        },
        findings_overview: {
          fix_rate: 0.75,
        },
      },
      isLoading: false,
    })
    mockUseCostAnalytics.mockReturnValue({
      data: {
        total_estimated_cost: 18.4,
        workflow_breakdown: [
          {
            label: "debugging",
            total_estimated_cost: 7.2,
          },
        ],
      },
      isLoading: false,
    })
    mockUseMaturityAnalytics.mockReturnValue({
      data: {
        avg_leverage_score: 71.2,
        orchestration_adoption_rate: 0.33,
        team_orchestration_adoption_rate: 0.28,
        explicit_customization_adoption_rate: 0.61,
      },
      isLoading: false,
    })
  })

  it("renders leadership performance metrics", () => {
    render(<AdminPerformanceTab teamId={null} />)

    expect(screen.getByText("Leadership Performance")).toBeInTheDocument()
    expect(screen.getByText("Sessions / Engineer / Day")).toBeInTheDocument()
    expect(screen.getByText("Adoption")).toBeInTheDocument()
    expect(screen.getByText("Total Spend")).toBeInTheDocument()
    expect(screen.getByText("Quality & Delivery")).toBeInTheDocument()
    expect(screen.getByText("Cost & Adoption")).toBeInTheDocument()
    expect(screen.getByText("Top workflow spend slice:")).toBeInTheDocument()
  })
})
