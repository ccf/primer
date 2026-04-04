import { fireEvent, render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { AdminSystemTab } from "../admin-system-tab"

const mockUseSystemStats = vi.fn()
const mockUseActivationHub = vi.fn()
const mockUseMeasurementIntegrity = vi.fn()
const mockUseBackgroundJobs = vi.fn()
const mockUseBackfillWorkflowProfiles = vi.fn()

vi.mock("@/hooks/use-api-queries", () => ({
  useSystemStats: () => mockUseSystemStats(),
  useActivationHub: () => mockUseActivationHub(),
  useMeasurementIntegrity: () => mockUseMeasurementIntegrity(),
  useBackgroundJobs: () => mockUseBackgroundJobs(),
}))

vi.mock("@/hooks/use-api-mutations", () => ({
  useBackfillWorkflowProfiles: () => mockUseBackfillWorkflowProfiles(),
}))

describe("AdminSystemTab", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseBackfillWorkflowProfiles.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      data: null,
      error: null,
    })
    mockUseSystemStats.mockReturnValue({
      data: {
        total_engineers: 12,
        active_engineers: 10,
        total_teams: 3,
        total_sessions: 48,
        total_ingest_events: 120,
        pending_background_jobs: 2,
        running_background_jobs: 1,
        failed_background_jobs: 1,
        database_type: "SQLite",
      },
      isLoading: false,
    })
    mockUseBackgroundJobs.mockReturnValue({
      data: [
        {
          id: "job-1",
          job_type: "facet_extract_session",
          status: "pending",
          attempts: 0,
          max_attempts: 3,
          lease_expires_at: null,
          last_error: null,
          created_by_engineer_id: null,
          enqueued_at: "2026-04-01T00:00:00Z",
          started_at: null,
          finished_at: null,
        },
      ],
      isLoading: false,
    })
    mockUseActivationHub.mockReturnValue({
      data: {
        ready_count: 2,
        total_items: 6,
        progress_pct: 33.3,
        items: [
          {
            key: "github",
            title: "GitHub",
            status: "ready",
            summary: "4 repositories linked and 12 pull requests synced.",
            next_action: null,
          },
          {
            key: "budgets",
            title: "Budgets",
            status: "action_needed",
            summary: "No budgets are configured yet.",
            next_action: "Create a budget in FinOps so burn-rate alerts and projections can work.",
          },
        ],
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
        sessions_with_workflow_profiles: 24,
        facet_coverage_pct: 100,
        transcript_coverage_pct: 83.3,
        workflow_profile_coverage_pct: 50,
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
        workflow_profile_quality: [
          {
            agent_type: "claude_code",
            session_count: 18,
            sessions_with_workflow_profiles: 18,
            workflow_profile_coverage_pct: 100,
          },
          {
            agent_type: "cursor",
            session_count: 30,
            sessions_with_workflow_profiles: 6,
            workflow_profile_coverage_pct: 20,
          },
        ],
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
            approval_signals_parity: "unavailable",
            approval_signals_coverage_pct: 0,
            change_signals_parity: "unavailable",
            change_signals_coverage_pct: 0,
            context_usage_parity: "unavailable",
            context_usage_coverage_pct: 0,
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
            approval_signals_parity: "optional",
            approval_signals_coverage_pct: 40,
            change_signals_parity: "optional",
            change_signals_coverage_pct: 30,
            context_usage_parity: "optional",
            context_usage_coverage_pct: 50,
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
    expect(screen.getByText("Activation Hub")).toBeInTheDocument()
    expect(screen.getByText("Setup Progress")).toBeInTheDocument()
    expect(screen.getByText("GitHub")).toBeInTheDocument()
    expect(screen.getByText("Budgets")).toBeInTheDocument()
    expect(screen.getByText("Create a budget in FinOps so burn-rate alerts and projections can work.")).toBeInTheDocument()
    expect(screen.getByText("Repository Metadata")).toBeInTheDocument()
    expect(screen.getByText("Schema Parity by Source")).toBeInTheDocument()
    expect(screen.getByText("Workflow Coverage")).toBeInTheDocument()
    expect(screen.getByText("Repository Coverage")).toBeInTheDocument()
    expect(screen.getByText("Recent Background Jobs")).toBeInTheDocument()
    expect(screen.getByText("facet extract session")).toBeInTheDocument()
    expect(screen.getAllByText("claude_code").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("cursor").length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText("acme/complete-repo")).toBeInTheDocument()
    expect(screen.getByText("acme/pending-repo")).toBeInTheDocument()
    expect(screen.getByText("Native Discovery")).toBeInTheDocument()
    expect(screen.getAllByText("Required").length).toBeGreaterThan(0)
    expect(screen.getAllByText("-").length).toBeGreaterThan(0)
    expect(screen.getByText("73.3%")).toBeInTheDocument()
    expect(screen.getAllByText("50.0%").length).toBeGreaterThan(0)
    expect(screen.getAllByText("Not expected").length).toBeGreaterThan(0)
    expect(screen.getByText("75.0%")).toBeInTheDocument()
    expect(screen.getByText("66.7%")).toBeInTheDocument()
    expect(screen.getByText("Checked")).toBeInTheDocument()
    expect(screen.getByText("Pending")).toBeInTheDocument()
  })

  it("triggers workflow profile backfill and recompute actions", () => {
    const mutate = vi.fn()
    mockUseBackfillWorkflowProfiles.mockReturnValue({
      mutate,
      isPending: false,
      data: null,
      error: null,
    })
    mockUseMeasurementIntegrity.mockReturnValue({
      data: {
        total_sessions: 1,
        sessions_with_messages: 1,
        sessions_with_facets: 1,
        sessions_with_workflow_profiles: 1,
        facet_coverage_pct: 100,
        transcript_coverage_pct: 100,
        workflow_profile_coverage_pct: 100,
        sessions_with_commit_sync_target: 0,
        sessions_with_linked_pull_requests: 0,
        github_sync_coverage_pct: 0,
        repositories_in_scope: 0,
        repositories_with_complete_metadata: 0,
        repositories_with_readiness_check: 0,
        repository_metadata_coverage_pct: 0,
        sessions_missing_transcript_telemetry: 0,
        sessions_missing_tool_telemetry: 0,
        sessions_missing_model_telemetry: 0,
        low_confidence_sessions: 0,
        missing_confidence_sessions: 0,
        legacy_outcome_sessions: 0,
        legacy_goal_category_sessions: 0,
        remaining_legacy_rows: 0,
        source_quality: [],
        repository_quality: [],
        workflow_profile_quality: [],
      },
      isLoading: false,
    })
    mockUseBackgroundJobs.mockReturnValue({
      data: [],
      isLoading: false,
    })
    mockUseActivationHub.mockReturnValue({
      data: {
        ready_count: 1,
        total_items: 6,
        progress_pct: 16.7,
        items: [],
      },
      isLoading: false,
    })

    render(<AdminSystemTab />)

    fireEvent.click(screen.getByRole("button", { name: /backfill workflow profiles/i }))
    fireEvent.click(screen.getByRole("button", { name: /recompute workflow profiles/i }))

    expect(mutate).toHaveBeenNthCalledWith(1, { limit: 5000, recompute: false, dryRun: false })
    expect(mutate).toHaveBeenNthCalledWith(2, { limit: 5000, recompute: true, dryRun: false })
  })
})
