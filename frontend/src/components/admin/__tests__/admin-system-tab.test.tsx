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

  it("renders measurement integrity coverage dashboards", () => {
    mockUseMeasurementIntegrity.mockReturnValue({
      data: {
        total_sessions: 48,
        sessions_with_messages: 40,
        sessions_with_facets: 18,
        facet_coverage_pct: 100,
        transcript_coverage_pct: 83.3,
        sessions_with_commit_sync_target: 12,
        sessions_with_linked_pull_requests: 9,
        github_sync_coverage_pct: 75,
        repositories_in_scope: 3,
        repositories_with_complete_metadata: 2,
        repositories_with_readiness_check: 2,
        repository_metadata_coverage_pct: 66.7,
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
            tool_call_parity: "optional",
            tool_call_coverage_pct: 0,
            model_usage_parity: "optional",
            model_usage_coverage_pct: 0,
            facet_parity: "optional",
            facet_coverage_pct: 0,
            native_discovery_parity: "required",
          },
        ],
        repository_quality: [
          {
            repository_full_name: "acme/complete-repo",
            session_count: 12,
            sessions_with_commits: 8,
            sessions_with_linked_pull_requests: 8,
            github_sync_coverage_pct: 100,
            has_github_id: true,
            has_default_branch: true,
            metadata_coverage_pct: 100,
            readiness_checked: true,
          },
          {
            repository_full_name: "acme/pending-repo",
            session_count: 6,
            sessions_with_commits: 0,
            sessions_with_linked_pull_requests: 0,
            github_sync_coverage_pct: null,
            has_github_id: false,
            has_default_branch: false,
            metadata_coverage_pct: 0,
            readiness_checked: false,
          },
        ],
      },
      isLoading: false,
    })

    render(<AdminSystemTab />)

    expect(screen.getAllByText("GitHub Sync").length).toBeGreaterThan(0)
    expect(screen.getByText("Repository Metadata")).toBeInTheDocument()
    expect(screen.getByText("Schema Parity by Source")).toBeInTheDocument()
    expect(screen.getByText("Repository Coverage")).toBeInTheDocument()
    expect(screen.getByText("claude_code")).toBeInTheDocument()
    expect(screen.getByText("cursor")).toBeInTheDocument()
    expect(screen.getByText("acme/complete-repo")).toBeInTheDocument()
    expect(screen.getByText("acme/pending-repo")).toBeInTheDocument()
    expect(screen.getByText("Native Discovery")).toBeInTheDocument()
    expect(screen.getAllByText("Required").length).toBeGreaterThan(0)
    expect(screen.getAllByText("-").length).toBeGreaterThan(0)
    expect(screen.getByText("73.3%")).toBeInTheDocument()
    expect(screen.getAllByText("Not expected").length).toBeGreaterThan(0)
    expect(screen.getByText("75.0%")).toBeInTheDocument()
    expect(screen.getByText("66.7%")).toBeInTheDocument()
    expect(screen.getByText("Checked")).toBeInTheDocument()
    expect(screen.getByText("Pending")).toBeInTheDocument()
  })
})
