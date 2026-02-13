import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/api", () => ({
  apiFetch: vi.fn(),
}))

import { apiFetch } from "@/lib/api"
import {
  useTeams,
  useEngineers,
  useOverview,
  useDailyStats,
  useFriction,
  useToolRankings,
  useModelRankings,
  useRecommendations,
  useSessions,
  useSessionDetail,
} from "../use-api-queries"

const mockApiFetch = vi.mocked(apiFetch)

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

beforeEach(() => {
  mockApiFetch.mockReset()
})

describe("useTeams", () => {
  it("calls apiFetch with /api/v1/teams", async () => {
    mockApiFetch.mockResolvedValue([])
    const { result } = renderHook(() => useTeams(), { wrapper: createWrapper() })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/teams")
  })
})

describe("useEngineers", () => {
  it("calls apiFetch with /api/v1/engineers", async () => {
    mockApiFetch.mockResolvedValue([])
    const { result } = renderHook(() => useEngineers(), { wrapper: createWrapper() })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/engineers")
  })
})

describe("useOverview", () => {
  it("calls apiFetch with /api/v1/analytics/overview when teamId is null", async () => {
    mockApiFetch.mockResolvedValue({})
    const { result } = renderHook(() => useOverview(null), { wrapper: createWrapper() })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/analytics/overview")
  })

  it("calls apiFetch with team_id query param when teamId is provided", async () => {
    mockApiFetch.mockResolvedValue({})
    const { result } = renderHook(() => useOverview("t1"), { wrapper: createWrapper() })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/analytics/overview?team_id=t1")
  })
})

describe("useDailyStats", () => {
  it("calls apiFetch with ?days=30 when teamId is null", async () => {
    mockApiFetch.mockResolvedValue([])
    const { result } = renderHook(() => useDailyStats(null), { wrapper: createWrapper() })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/analytics/daily?days=30")
  })

  it("calls apiFetch with team_id and days when teamId is provided", async () => {
    mockApiFetch.mockResolvedValue([])
    const { result } = renderHook(() => useDailyStats("t1"), { wrapper: createWrapper() })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/analytics/daily?team_id=t1&days=30")
  })
})

describe("useFriction", () => {
  it("calls apiFetch with team_id when teamId is provided", async () => {
    mockApiFetch.mockResolvedValue([])
    const { result } = renderHook(() => useFriction("t1"), { wrapper: createWrapper() })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/analytics/friction?team_id=t1")
  })
})

describe("useToolRankings", () => {
  it("calls apiFetch with correct path", async () => {
    mockApiFetch.mockResolvedValue([])
    const { result } = renderHook(() => useToolRankings("t1"), { wrapper: createWrapper() })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/analytics/tools?team_id=t1")
  })
})

describe("useModelRankings", () => {
  it("calls apiFetch with correct path", async () => {
    mockApiFetch.mockResolvedValue([])
    const { result } = renderHook(() => useModelRankings("t1"), { wrapper: createWrapper() })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/analytics/models?team_id=t1")
  })
})

describe("useRecommendations", () => {
  it("calls apiFetch with correct path", async () => {
    mockApiFetch.mockResolvedValue([])
    const { result } = renderHook(() => useRecommendations("t1"), { wrapper: createWrapper() })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/analytics/recommendations?team_id=t1")
  })
})

describe("useSessions", () => {
  it("calls apiFetch with all params in query string", async () => {
    mockApiFetch.mockResolvedValue([])
    const { result } = renderHook(
      () =>
        useSessions({
          teamId: "t1",
          engineerId: "e1",
          limit: 25,
          offset: 50,
        }),
      { wrapper: createWrapper() },
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockApiFetch).toHaveBeenCalledWith(
      "/api/v1/sessions?team_id=t1&engineer_id=e1&limit=25&offset=50",
    )
  })

  it("calls apiFetch with /api/v1/sessions when no optional params", async () => {
    mockApiFetch.mockResolvedValue([])
    const { result } = renderHook(() => useSessions({ teamId: null }), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/sessions")
  })
})

describe("useSessionDetail", () => {
  it("calls apiFetch with /api/v1/sessions/s1", async () => {
    mockApiFetch.mockResolvedValue({})
    const { result } = renderHook(() => useSessionDetail("s1"), { wrapper: createWrapper() })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/sessions/s1")
  })

  it("does not call apiFetch when sessionId is empty string", async () => {
    mockApiFetch.mockResolvedValue({})
    const { result } = renderHook(() => useSessionDetail(""), { wrapper: createWrapper() })

    // The query should not be enabled, so it stays in pending/idle state
    // Wait a tick to make sure it does not fire
    await new Promise((r) => setTimeout(r, 50))
    expect(result.current.fetchStatus).toBe("idle")
    expect(mockApiFetch).not.toHaveBeenCalled()
  })
})
