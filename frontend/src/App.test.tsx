import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("@/lib/api", () => ({
  getApiKey: vi.fn(),
  setApiKey: vi.fn(),
  clearApiKey: vi.fn(),
  apiFetch: vi.fn(),
}))

vi.mock("@/hooks/use-api-queries", () => ({
  useTeams: vi.fn(),
  useOverview: vi.fn().mockReturnValue({ data: undefined, isLoading: true }),
  useDailyStats: vi.fn().mockReturnValue({ data: undefined, isLoading: true }),
  useToolRankings: vi.fn().mockReturnValue({ data: undefined, isLoading: true }),
  useModelRankings: vi.fn().mockReturnValue({ data: undefined, isLoading: true }),
  useRecommendations: vi.fn().mockReturnValue({ data: undefined, isLoading: true }),
  useEngineers: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useSessions: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useSessionDetail: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useFriction: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
}))

import { getApiKey } from "@/lib/api"
import { useTeams } from "@/hooks/use-api-queries"
import App from "./App"

const mockGetApiKey = vi.mocked(getApiKey)
const mockUseTeams = vi.mocked(useTeams)

describe("App", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetApiKey.mockReturnValue(null)
    mockUseTeams.mockReturnValue({ data: [], isLoading: false } as unknown as ReturnType<
      typeof useTeams
    >)
  })

  it("shows LoginGate when no API key is set", () => {
    mockGetApiKey.mockReturnValue(null)

    render(<App />)
    expect(screen.getByText("Primer Dashboard")).toBeInTheDocument()
    expect(screen.getByPlaceholderText("primer-admin-dev-key")).toBeInTheDocument()
  })

  it("shows app shell with navigation when API key is present", () => {
    mockGetApiKey.mockReturnValue("test-key")
    mockUseTeams.mockReturnValue({ data: [], isLoading: false } as unknown as ReturnType<
      typeof useTeams
    >)

    render(<App />)
    // Sidebar navigation links
    expect(screen.getByText("Primer")).toBeInTheDocument()
    expect(screen.getByText("Overview")).toBeInTheDocument()
    expect(screen.getByText("Sessions")).toBeInTheDocument()
    expect(screen.getByText("Engineers")).toBeInTheDocument()
  })
})
