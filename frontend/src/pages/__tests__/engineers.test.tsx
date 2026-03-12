import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"

vi.mock("@/lib/api", () => ({
  getApiKey: vi.fn().mockReturnValue(null),
  clearApiKey: vi.fn(),
}))

vi.mock("@/lib/auth-context", () => ({
  useAuth: vi.fn().mockReturnValue({ user: null }),
}))

vi.mock("@/hooks/use-api-queries", () => ({
  useEngineers: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useEngineerAnalytics: vi.fn(),
  useEngineerBenchmarks: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useQualityMetrics: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useMaturityAnalytics: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useTeams: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useTeam: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useOverview: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useDailyStats: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useToolRankings: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useModelRankings: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useRecommendations: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useCostAnalytics: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useActivityHeatmap: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useSessions: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useSessionDetail: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useTranscript: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useFriction: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useProjectAnalytics: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useProjectComparison: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
}))

import { useEngineerAnalytics } from "@/hooks/use-api-queries"
import { EngineersPage } from "../engineers"

const mockUseEngineerAnalytics = vi.mocked(useEngineerAnalytics)

const mockEngineerData = {
  engineers: [
    {
      engineer_id: "e1",
      name: "Alice",
      email: "a@t.com",
      avatar_url: null,
      github_username: null,
      team_id: null,
      total_sessions: 10,
      total_tokens: 5000,
      estimated_cost: 1.5,
      success_rate: 0.9,
      avg_duration: 120,
      top_tools: ["Read", "Edit"],
    },
  ],
}

describe("EngineersPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseEngineerAnalytics.mockReturnValue({
      data: undefined,
      isLoading: false,
    } as ReturnType<typeof useEngineerAnalytics>)
  })

  const renderPage = () =>
    render(
      <MemoryRouter>
        <EngineersPage teamId={null} dateRange={null} />
      </MemoryRouter>,
    )

  it("shows loading skeleton when isLoading is true", () => {
    mockUseEngineerAnalytics.mockReturnValue({
      data: undefined,
      isLoading: true,
    } as ReturnType<typeof useEngineerAnalytics>)

    renderPage()
    expect(screen.getByText("Engineers")).toBeInTheDocument()
  })

  it("shows empty state when no engineers", () => {
    mockUseEngineerAnalytics.mockReturnValue({
      data: { engineers: [] },
      isLoading: false,
    } as unknown as ReturnType<typeof useEngineerAnalytics>)

    renderPage()
    expect(screen.getByText("No engineers found")).toBeInTheDocument()
  })

  it("renders engineer leaderboard when data is present", () => {
    mockUseEngineerAnalytics.mockReturnValue({
      data: mockEngineerData,
      isLoading: false,
    } as unknown as ReturnType<typeof useEngineerAnalytics>)

    renderPage()
    expect(screen.getByText("Alice")).toBeInTheDocument()
  })
})
