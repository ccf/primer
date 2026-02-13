import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"

vi.mock("@/hooks/use-api-queries", () => ({
  useSessions: vi.fn(),
  useEngineers: vi.fn(),
  useFriction: vi.fn(),
  useTeams: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useOverview: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useDailyStats: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useToolRankings: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useModelRankings: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useRecommendations: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useSessionDetail: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
}))

import { useSessions, useEngineers, useFriction } from "@/hooks/use-api-queries"
import { SessionsPage } from "../sessions"

const mockUseSessions = vi.mocked(useSessions)
const mockUseEngineers = vi.mocked(useEngineers)
const mockUseFriction = vi.mocked(useFriction)

const mockSession = {
  id: "s1",
  engineer_id: "e1",
  project_path: null,
  project_name: "my-project",
  git_branch: null,
  claude_version: null,
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
  first_prompt: null,
  summary: null,
  has_facets: true,
  created_at: "2025-01-15T10:00:00",
}

describe("SessionsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseSessions.mockReturnValue({ data: undefined, isLoading: false } as ReturnType<
      typeof useSessions
    >)
    mockUseEngineers.mockReturnValue({ data: [], isLoading: false } as unknown as ReturnType<
      typeof useEngineers
    >)
    mockUseFriction.mockReturnValue({ data: undefined, isLoading: false } as ReturnType<
      typeof useFriction
    >)
  })

  const renderPage = (teamId: string | null = null) =>
    render(
      <MemoryRouter>
        <SessionsPage teamId={teamId} />
      </MemoryRouter>,
    )

  it("shows heading 'Sessions'", () => {
    renderPage()
    expect(screen.getByText("Sessions")).toBeInTheDocument()
  })

  it("shows loading skeleton when sessions are loading", () => {
    mockUseSessions.mockReturnValue({ data: undefined, isLoading: true } as ReturnType<
      typeof useSessions
    >)
    const { container } = renderPage()
    expect(container.querySelector(".space-y-3")).toBeInTheDocument()
  })

  it("shows empty state when no sessions", () => {
    mockUseSessions.mockReturnValue({ data: [], isLoading: false } as unknown as ReturnType<
      typeof useSessions
    >)
    renderPage()
    expect(screen.getByText("No sessions found")).toBeInTheDocument()
  })

  it("renders session table when data is present", () => {
    mockUseSessions.mockReturnValue({
      data: [mockSession],
      isLoading: false,
    } as unknown as ReturnType<typeof useSessions>)
    renderPage()
    expect(screen.getByText("my-project")).toBeInTheDocument()
  })

  it("renders pagination showing range", () => {
    mockUseSessions.mockReturnValue({
      data: [mockSession],
      isLoading: false,
    } as unknown as ReturnType<typeof useSessions>)
    renderPage()
    expect(screen.getByText(/Showing 1/)).toBeInTheDocument()
  })

  it("Previous button is disabled on first page", () => {
    mockUseSessions.mockReturnValue({
      data: [mockSession],
      isLoading: false,
    } as unknown as ReturnType<typeof useSessions>)
    renderPage()
    expect(screen.getByRole("button", { name: /previous/i })).toBeDisabled()
  })

  it("Next button is disabled when results < PAGE_SIZE", () => {
    mockUseSessions.mockReturnValue({
      data: [mockSession],
      isLoading: false,
    } as unknown as ReturnType<typeof useSessions>)
    renderPage()
    expect(screen.getByRole("button", { name: /next/i })).toBeDisabled()
  })

  it("renders friction list when friction data present", () => {
    mockUseSessions.mockReturnValue({
      data: [mockSession],
      isLoading: false,
    } as unknown as ReturnType<typeof useSessions>)
    mockUseFriction.mockReturnValue({
      data: [{ friction_type: "tool_error", count: 5, details: ["error"] }],
      isLoading: false,
    } as unknown as ReturnType<typeof useFriction>)
    renderPage()
    expect(screen.getByText("Friction Report")).toBeInTheDocument()
    expect(screen.getByText("tool_error")).toBeInTheDocument()
  })

  it("shows loading skeleton for friction when loadingFriction is true", () => {
    mockUseSessions.mockReturnValue({
      data: [mockSession],
      isLoading: false,
    } as unknown as ReturnType<typeof useSessions>)
    mockUseFriction.mockReturnValue({
      data: undefined,
      isLoading: true,
    } as ReturnType<typeof useFriction>)
    const { container } = renderPage()
    const skeletons = container.querySelectorAll(".animate-pulse")
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it("renders engineer filter with options", () => {
    mockUseEngineers.mockReturnValue({
      data: [{ id: "e1", name: "Alice", email: "a@t.com", team_id: "t1", created_at: "2025-01-01T00:00:00" }],
      isLoading: false,
    } as unknown as ReturnType<typeof useEngineers>)
    renderPage()
    expect(screen.getByText("All engineers")).toBeInTheDocument()
    expect(screen.getByText("Alice")).toBeInTheDocument()
  })
})
