import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"

vi.mock("@/hooks/use-api-queries", () => ({
  useEngineers: vi.fn(),
  useTeams: vi.fn(),
  useOverview: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useDailyStats: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useToolRankings: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useModelRankings: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useRecommendations: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useSessions: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useSessionDetail: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useFriction: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
}))

import { useEngineers, useTeams } from "@/hooks/use-api-queries"
import { EngineersPage } from "../engineers"

const mockUseEngineers = vi.mocked(useEngineers)
const mockUseTeams = vi.mocked(useTeams)

const mockEngineers = [
  {
    id: "e1",
    name: "Alice",
    email: "a@t.com",
    team_id: "t1",
    created_at: "2025-01-15T00:00:00",
  },
]

const mockTeams = [
  {
    id: "t1",
    name: "Platform",
    created_at: "2025-01-01T00:00:00",
  },
]

describe("EngineersPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseEngineers.mockReturnValue({ data: undefined, isLoading: false } as ReturnType<
      typeof useEngineers
    >)
    mockUseTeams.mockReturnValue({ data: undefined, isLoading: false } as ReturnType<
      typeof useTeams
    >)
  })

  const renderPage = () =>
    render(
      <MemoryRouter>
        <EngineersPage />
      </MemoryRouter>,
    )

  it("shows loading skeleton when isLoading is true", () => {
    mockUseEngineers.mockReturnValue({ data: undefined, isLoading: true } as ReturnType<
      typeof useEngineers
    >)
    mockUseTeams.mockReturnValue({ data: undefined, isLoading: true } as ReturnType<
      typeof useTeams
    >)

    renderPage()
    expect(screen.getByText("Engineers")).toBeInTheDocument()
  })

  it("shows empty state when no engineers", () => {
    mockUseEngineers.mockReturnValue({ data: [], isLoading: false } as unknown as ReturnType<
      typeof useEngineers
    >)
    mockUseTeams.mockReturnValue({ data: mockTeams, isLoading: false } as unknown as ReturnType<
      typeof useTeams
    >)

    renderPage()
    expect(screen.getByText("No engineers found")).toBeInTheDocument()
  })

  it("renders engineer table when data is present", () => {
    mockUseEngineers.mockReturnValue({
      data: mockEngineers,
      isLoading: false,
    } as unknown as ReturnType<typeof useEngineers>)
    mockUseTeams.mockReturnValue({ data: mockTeams, isLoading: false } as unknown as ReturnType<
      typeof useTeams
    >)

    renderPage()
    expect(screen.getByText("Alice")).toBeInTheDocument()
    expect(screen.getByText("a@t.com")).toBeInTheDocument()
    expect(screen.getByText("Platform")).toBeInTheDocument()
  })
})
