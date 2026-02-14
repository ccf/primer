import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"

vi.mock("@/lib/auth-context", () => ({
  useAuth: vi.fn().mockReturnValue({ user: null }),
}))

vi.mock("@/hooks/use-api-queries", () => ({
  useOverview: vi.fn(),
  useDailyStats: vi.fn(),
  useToolRankings: vi.fn(),
  useModelRankings: vi.fn(),
  useRecommendations: vi.fn(),
  useProductivity: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useCostAnalytics: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useActivityHeatmap: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useTeams: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useEngineers: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useEngineerAnalytics: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useSessions: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useSessionDetail: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useTranscript: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useFriction: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useTeam: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useProjectAnalytics: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
}))

import {
  useOverview,
  useDailyStats,
  useToolRankings,
  useModelRankings,
  useRecommendations,
} from "@/hooks/use-api-queries"
import { OverviewPage } from "../overview"

const mockUseOverview = vi.mocked(useOverview)
const mockUseDailyStats = vi.mocked(useDailyStats)
const mockUseToolRankings = vi.mocked(useToolRankings)
const mockUseModelRankings = vi.mocked(useModelRankings)
const mockUseRecommendations = vi.mocked(useRecommendations)

const mockOverview = {
  total_sessions: 100,
  total_engineers: 5,
  total_messages: 500,
  total_tool_calls: 200,
  total_input_tokens: 50000,
  total_output_tokens: 25000,
  estimated_cost: 12.50,
  avg_session_duration: 120,
  avg_messages_per_session: 5,
  outcome_counts: { success: 80, partial: 20 },
  session_type_counts: { feature: 60, debugging: 40 },
}

describe("OverviewPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseOverview.mockReturnValue({ data: undefined, isLoading: false } as ReturnType<
      typeof useOverview
    >)
    mockUseDailyStats.mockReturnValue({ data: undefined, isLoading: false } as ReturnType<
      typeof useDailyStats
    >)
    mockUseToolRankings.mockReturnValue({ data: undefined, isLoading: false } as ReturnType<
      typeof useToolRankings
    >)
    mockUseModelRankings.mockReturnValue({ data: undefined, isLoading: false } as ReturnType<
      typeof useModelRankings
    >)
    mockUseRecommendations.mockReturnValue({ data: undefined, isLoading: false } as ReturnType<
      typeof useRecommendations
    >)
  })

  const renderPage = () =>
    render(
      <MemoryRouter>
        <OverviewPage teamId={null} dateRange={null} />
      </MemoryRouter>,
    )

  it("shows loading skeletons when overview is loading", () => {
    mockUseOverview.mockReturnValue({ data: undefined, isLoading: true } as ReturnType<
      typeof useOverview
    >)

    const { container } = renderPage()
    // Loading state renders a grid of CardSkeleton elements and a ChartSkeleton
    expect(container.querySelector(".grid")).toBeInTheDocument()
  })

  it("returns null when no overview data and not loading", () => {
    mockUseOverview.mockReturnValue({ data: undefined, isLoading: false } as ReturnType<
      typeof useOverview
    >)

    const { container } = renderPage()
    // The OverviewPage returns null, so nothing renders inside the wrapper
    expect(screen.queryByText("Overview")).not.toBeInTheDocument()
    expect(container.innerHTML).toBe("")
  })

  it("renders 'Overview' heading and stat cards when data is present", () => {
    mockUseOverview.mockReturnValue({
      data: mockOverview,
      isLoading: false,
    } as unknown as ReturnType<typeof useOverview>)
    mockUseDailyStats.mockReturnValue({ data: [], isLoading: false } as unknown as ReturnType<
      typeof useDailyStats
    >)
    mockUseToolRankings.mockReturnValue({ data: [], isLoading: false } as unknown as ReturnType<
      typeof useToolRankings
    >)
    mockUseModelRankings.mockReturnValue({ data: [], isLoading: false } as unknown as ReturnType<
      typeof useModelRankings
    >)
    mockUseRecommendations.mockReturnValue({
      data: [],
      isLoading: false,
    } as unknown as ReturnType<typeof useRecommendations>)

    renderPage()
    expect(screen.getByText("Overview")).toBeInTheDocument()
    expect(screen.getByText("Total Sessions")).toBeInTheDocument()
    expect(screen.getByText("Engineers")).toBeInTheDocument()
    expect(screen.getByText("Messages")).toBeInTheDocument()
    expect(screen.getByText("Tool Calls")).toBeInTheDocument()
  })
})
