import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { AdminSystemTab } from "../admin-system-tab"

const mockUseSystemStats = vi.fn()
const mockUseMeasurementIntegrity = vi.fn()

vi.mock("@/hooks/use-api-queries", () => ({
  useSystemStats: () => mockUseSystemStats(),
  useMeasurementIntegrity: () => mockUseMeasurementIntegrity(),
}))

describe("AdminSystemTab", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseSystemStats.mockReturnValue({
      data: {
        total_engineers: 12,
        active_engineers: 10,
        total_teams: 3,
        total_sessions: 48,
        total_ingest_events: 120,
        database_type: "SQLite",
      },
      isLoading: false,
    })
  })

  it("renders schema parity coverage by source", () => {
    mockUseMeasurementIntegrity.mockReturnValue({
      data: {
        total_sessions: 48,
        sessions_with_messages: 40,
        sessions_with_facets: 18,
        facet_coverage_pct: 100,
        transcript_coverage_pct: 83.3,
        sessions_missing_transcript_telemetry: 8,
        sessions_missing_tool_telemetry: 2,
        sessions_missing_model_telemetry: 2,
        low_confidence_sessions: 3,
        missing_confidence_sessions: 1,
        legacy_outcome_sessions: 0,
        legacy_goal_category_sessions: 0,
        remaining_legacy_rows: 0,
        source_quality: [
          {
            agent_type: "claude_code",
            session_count: 18,
            transcript_parity: "required",
            transcript_coverage_pct: 100,
            tool_call_parity: "required",
            tool_call_coverage_pct: 94.4,
            model_usage_parity: "required",
            model_usage_coverage_pct: 94.4,
            facet_parity: "required",
            facet_coverage_pct: 100,
            native_discovery_parity: "required",
          },
          {
            agent_type: "cursor",
            session_count: 30,
            transcript_parity: "required",
            transcript_coverage_pct: 73.3,
            tool_call_parity: "unavailable",
            tool_call_coverage_pct: 0,
            model_usage_parity: "unavailable",
            model_usage_coverage_pct: 0,
            facet_parity: "unavailable",
            facet_coverage_pct: 0,
            native_discovery_parity: "unavailable",
          },
        ],
      },
      isLoading: false,
    })

    render(<AdminSystemTab />)

    expect(screen.getByText("Schema Parity by Source")).toBeInTheDocument()
    expect(screen.getByText("claude_code")).toBeInTheDocument()
    expect(screen.getByText("cursor")).toBeInTheDocument()
    expect(screen.getByText("Native Discovery")).toBeInTheDocument()
    expect(screen.getAllByText("Unavailable").length).toBeGreaterThan(0)
    expect(screen.getByText("73.3%")).toBeInTheDocument()
    expect(screen.getAllByText("Not expected").length).toBeGreaterThan(0)
  })
})
