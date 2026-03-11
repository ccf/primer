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
  useTeam: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useOverview: vi.fn().mockReturnValue({ data: undefined, isLoading: true }),
  useDailyStats: vi.fn().mockReturnValue({ data: undefined, isLoading: true }),
  useToolRankings: vi.fn().mockReturnValue({ data: undefined, isLoading: true }),
  useModelRankings: vi.fn().mockReturnValue({ data: undefined, isLoading: true }),
  useRecommendations: vi.fn().mockReturnValue({ data: undefined, isLoading: true }),
  useProductivity: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useCostAnalytics: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useActivityHeatmap: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useAlerts: vi.fn().mockReturnValue({ data: [], isLoading: false }),
  useEngineers: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useEngineerAnalytics: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useEngineerBenchmarks: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useEngineerProfile: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useBottleneckAnalytics: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useToolAdoption: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useSkillInventory: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useQualityMetrics: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useClaudePRComparison: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  usePersonalizedTips: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useConfigOptimization: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useLearningPaths: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useTimeToTeamAverage: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useSessions: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useSessionDetail: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useTranscript: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useFriction: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useProjectAnalytics: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useInterventions: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useSystemStats: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useMeasurementIntegrity: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
  useIngestEvents: vi.fn().mockReturnValue({ data: undefined, isLoading: false }),
}))

vi.mock("@/hooks/use-api-mutations", () => ({
  useAcknowledgeAlert: vi.fn().mockReturnValue({ mutate: vi.fn() }),
  useDismissAlert: vi.fn().mockReturnValue({ mutate: vi.fn() }),
  useDeactivateEngineer: vi.fn().mockReturnValue({ mutate: vi.fn() }),
  useRotateApiKey: vi.fn().mockReturnValue({ mutate: vi.fn() }),
  useUpdateEngineerRole: vi.fn().mockReturnValue({ mutate: vi.fn() }),
  useCreateTeam: vi.fn().mockReturnValue({ mutate: vi.fn() }),
  useCreateEngineer: vi.fn().mockReturnValue({ mutate: vi.fn() }),
  useCreateIntervention: vi.fn().mockReturnValue({ mutate: vi.fn(), isPending: false }),
  useUpdateIntervention: vi.fn().mockReturnValue({ mutate: vi.fn() }),
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
    expect(screen.getByText("Primer")).toBeInTheDocument()
    expect(screen.getByText("Sign in with GitHub")).toBeInTheDocument()
  })

  it("shows app shell with navigation when API key is present", () => {
    mockGetApiKey.mockReturnValue("test-key")
    mockUseTeams.mockReturnValue({ data: [], isLoading: false } as unknown as ReturnType<
      typeof useTeams
    >)

    render(<App />)
    // Sidebar navigation links (leadership role for API key users)
    expect(screen.getByText("Primer")).toBeInTheDocument()
    expect(screen.getByText("My Profile")).toBeInTheDocument()
    expect(screen.getByText("Organization")).toBeInTheDocument()
    expect(screen.getByText("Sessions")).toBeInTheDocument()
    expect(screen.getByText("Engineers")).toBeInTheDocument()
  })
})
