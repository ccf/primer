import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom")
  return { ...actual, useParams: () => ({ id: "s1" }) }
})

vi.mock("@/hooks/use-api-queries", () => ({
  useSessionDetail: vi.fn(),
  useTranscript: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useTeams: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useTeam: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useEngineers: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useEngineerAnalytics: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useOverview: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useDailyStats: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useToolRankings: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useModelRankings: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useRecommendations: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useCostAnalytics: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useActivityHeatmap: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useSessions: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useFriction: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useProjectAnalytics: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useProjectComparison: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useSimilarSessions: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
}))

import { useSessionDetail } from "@/hooks/use-api-queries"
import { SessionDetailPage } from "../session-detail"

const mockUseSessionDetail = vi.mocked(useSessionDetail)

const mockSession = {
  id: "s1",
  engineer_id: "e1",
  project_path: null,
  project_name: "my-project",
  git_branch: null,
  agent_type: "claude_code",
  agent_version: null,
  permission_mode: null,
  end_reason: null,
  started_at: "2025-01-15T10:00:00",
  ended_at: null,
  duration_seconds: 120,
  message_count: 10,
  user_message_count: 5,
  assistant_message_count: 5,
  tool_call_count: 3,
  input_tokens: 1000,
  output_tokens: 500,
  cache_read_tokens: 0,
  cache_creation_tokens: 0,
  primary_model: "claude-sonnet-4-5-20250929",
  first_prompt: "Fix the login bug",
  summary: null,
  has_facets: true,
  created_at: "2025-01-15T10:00:00",
}

const mockDetailSession = {
  ...mockSession,
  facets: {
    underlying_goal: "Fix authentication",
    goal_categories: ["bugfix"],
    outcome: "success",
    session_type: "debugging",
    primary_success: "yes",
    agent_helpfulness: "very_helpful",
    brief_summary: "Fixed login flow",
    user_satisfaction_counts: null,
    friction_counts: null,
    friction_detail: null,
    created_at: "2025-01-15T10:00:00",
  },
  tool_usages: [{ tool_name: "Read", call_count: 10 }],
  model_usages: [
    {
      model_name: "claude-sonnet-4-5-20250929",
      input_tokens: 1000,
      output_tokens: 500,
      cache_read_tokens: 0,
      cache_creation_tokens: 0,
    },
  ],
}

describe("SessionDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseSessionDetail.mockReturnValue({
      data: undefined,
      isLoading: false,
    } as ReturnType<typeof useSessionDetail>)
  })

  const renderPage = () =>
    render(
      <MemoryRouter>
        <SessionDetailPage />
      </MemoryRouter>,
    )

  it("shows loading skeleton when isLoading is true", () => {
    mockUseSessionDetail.mockReturnValue({
      data: undefined,
      isLoading: true,
    } as ReturnType<typeof useSessionDetail>)

    const { container } = renderPage()
    // CardSkeleton renders Skeleton elements inside Card components
    expect(container.querySelector(".space-y-4")).toBeInTheDocument()
  })

  it("shows 'Session not found' when no data", () => {
    mockUseSessionDetail.mockReturnValue({
      data: undefined,
      isLoading: false,
    } as ReturnType<typeof useSessionDetail>)

    renderPage()
    expect(screen.getByText("Session not found")).toBeInTheDocument()
  })

  it("renders session detail panel when data is present", () => {
    mockUseSessionDetail.mockReturnValue({
      data: mockDetailSession,
      isLoading: false,
    } as unknown as ReturnType<typeof useSessionDetail>)

    renderPage()
    expect(screen.getByText("Back to sessions")).toBeInTheDocument()
    expect(screen.getByText("my-project")).toBeInTheDocument()
  })
})
