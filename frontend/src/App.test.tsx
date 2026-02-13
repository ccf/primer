import type React from "react"
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("@/lib/api", () => ({
  getApiKey: vi.fn(),
  setApiKey: vi.fn(),
  clearApiKey: vi.fn(),
  apiFetch: vi.fn(),
}))

vi.mock("@/lib/auth-context", async () => {
  const actual = await vi.importActual<typeof import("@/lib/auth-context")>("@/lib/auth-context")
  return {
    ...actual,
    AuthProvider: ({ children }: { children: React.ReactNode }) => children,
    useAuth: vi.fn(() => ({ user: null, loading: false, login: vi.fn(), logout: vi.fn() })),
  }
})

vi.mock("@/lib/theme-context", () => ({
  ThemeProvider: ({ children }: { children: React.ReactNode }) => children,
  useTheme: vi.fn(() => ({ theme: "light", resolved: "light", setTheme: vi.fn() })),
}))

vi.mock("@/hooks/use-api-queries", () => ({
  useTeams: vi.fn(),
  useOverview: vi.fn().mockReturnValue({ data: undefined, isLoading: true }),
  useDailyStats: vi.fn().mockReturnValue({ data: undefined, isLoading: true }),
  useToolRankings: vi.fn().mockReturnValue({ data: undefined, isLoading: true }),
  useModelRankings: vi.fn().mockReturnValue({ data: undefined, isLoading: true }),
  useRecommendations: vi.fn().mockReturnValue({ data: undefined, isLoading: true }),
  useCostAnalytics: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
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
    expect(screen.getByText("Sign in with GitHub")).toBeInTheDocument()
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
