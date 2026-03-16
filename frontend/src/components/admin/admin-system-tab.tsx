import {
  AlertTriangle,
  CheckCircle2,
  Database,
  FileInput,
  FileText,
  FolderKanban,
  FolderGit2,
  GitPullRequest,
  MonitorDot,
  RefreshCcw,
  Users,
} from "lucide-react"
import { useMeasurementIntegrity, useSystemStats } from "@/hooks/use-api-queries"
import { useBackfillWorkflowProfiles } from "@/hooks/use-api-mutations"
import { StatCard } from "@/components/dashboard/stat-card"
import { formatNumber } from "@/lib/utils"
import { CardSkeleton } from "@/components/shared/loading-skeleton"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type {
  AgentSourceQuality,
  MeasurementIntegrityStats,
  RepositoryQuality,
  TelemetryParity,
  WorkflowProfileCoverageRow,
} from "@/types/api"

function formatCoverage(value: number): string {
  return `${value.toFixed(1)}%`
}

function parityVariant(parity: TelemetryParity): "success" | "info" | "outline" {
  if (parity === "required") return "success"
  if (parity === "optional") return "info"
  return "outline"
}

function parityLabel(parity: TelemetryParity): string {
  if (parity === "required") return "Required"
  if (parity === "optional") return "Optional"
  return "Unavailable"
}

function CoverageCell({
  parity,
  coverage,
}: {
  parity: TelemetryParity
  coverage?: number
}) {
  const coverageLabel =
    parity === "unavailable" ? "Not expected" : coverage == null ? "-" : formatCoverage(coverage)

  return (
    <div className="space-y-1">
      <Badge variant={parityVariant(parity)}>{parityLabel(parity)}</Badge>
      <div className="text-xs text-muted-foreground">{coverageLabel}</div>
    </div>
  )
}

function SourceQualityTable({ rows }: { rows: AgentSourceQuality[] }) {
  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">No source-quality data yet.</p>
  }

  return (
    <Card>
      <CardHeader className="pb-4">
        <CardTitle>Schema Parity by Source</CardTitle>
        <p className="text-sm text-muted-foreground">
          Required fields count against coverage. Unavailable fields are excluded from integrity
          penalties.
        </p>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="text-left text-muted-foreground">
              <tr className="border-b border-border/60">
                <th className="pb-3 pr-4 font-medium">Agent</th>
                <th className="pb-3 pr-4 font-medium">Sessions</th>
                <th className="pb-3 pr-4 font-medium">Transcript</th>
                <th className="pb-3 pr-4 font-medium">Tool Calls</th>
                <th className="pb-3 pr-4 font-medium">Model Usage</th>
                <th className="pb-3 pr-4 font-medium">Facets</th>
                <th className="pb-3 font-medium">Native Discovery</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.agent_type} className="border-b border-border/40 last:border-b-0">
                  <td className="py-3 pr-4 font-medium">{row.agent_type}</td>
                  <td className="py-3 pr-4 text-muted-foreground">
                    {formatNumber(row.session_count)}
                  </td>
                  <td className="py-3 pr-4">
                    <CoverageCell
                      parity={row.transcript_parity}
                      coverage={row.transcript_coverage_pct}
                    />
                  </td>
                  <td className="py-3 pr-4">
                    <CoverageCell
                      parity={row.tool_call_parity}
                      coverage={row.tool_call_coverage_pct}
                    />
                  </td>
                  <td className="py-3 pr-4">
                    <CoverageCell
                      parity={row.model_usage_parity}
                      coverage={row.model_usage_coverage_pct}
                    />
                  </td>
                  <td className="py-3 pr-4">
                    <CoverageCell parity={row.facet_parity} coverage={row.facet_coverage_pct} />
                  </td>
                  <td className="py-3">
                    <CoverageCell parity={row.native_discovery_parity} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

function RepositoryMetadataCell({ row }: { row: RepositoryQuality }) {
  return (
    <div className="space-y-2">
      <div className="font-medium">{formatCoverage(row.metadata_coverage_pct)}</div>
      <div className="flex flex-wrap gap-1">
        <Badge variant={row.has_github_id ? "success" : "outline"}>GitHub ID</Badge>
        <Badge variant={row.has_default_branch ? "success" : "outline"}>Default Branch</Badge>
      </div>
    </div>
  )
}

function RepositorySyncCell({ row }: { row: RepositoryQuality }) {
  if (row.sessions_with_commits === 0) {
    return (
      <div className="space-y-1">
        <div className="font-medium">Not expected</div>
        <div className="text-xs text-muted-foreground">No commit sessions yet</div>
      </div>
    )
  }

  return (
    <div className="space-y-1">
      <div className="font-medium">{formatCoverage(row.github_sync_coverage_pct ?? 0)}</div>
      <div className="text-xs text-muted-foreground">
        {formatNumber(row.sessions_with_linked_pull_requests)} of{" "}
        {formatNumber(row.sessions_with_commits)} commit sessions linked
      </div>
    </div>
  )
}

function RepositoryQualityTable({ rows }: { rows: RepositoryQuality[] }) {
  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">No repository coverage data yet.</p>
  }

  return (
    <Card>
      <CardHeader className="pb-4">
        <CardTitle>Repository Coverage</CardTitle>
        <p className="text-sm text-muted-foreground">
          Repository metadata tracks linked repos with GitHub IDs and default branches. GitHub sync
          tracks whether repo-linked commit sessions are correlated to pull requests.
        </p>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="text-left text-muted-foreground">
              <tr className="border-b border-border/60">
                <th className="pb-3 pr-4 font-medium">Repository</th>
                <th className="pb-3 pr-4 font-medium">Sessions</th>
                <th className="pb-3 pr-4 font-medium">Metadata</th>
                <th className="pb-3 pr-4 font-medium">Readiness</th>
                <th className="pb-3 font-medium">GitHub Sync</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={row.repository_full_name}
                  className="border-b border-border/40 last:border-b-0"
                >
                  <td className="py-3 pr-4 font-medium">{row.repository_full_name}</td>
                  <td className="py-3 pr-4 text-muted-foreground">
                    {formatNumber(row.session_count)}
                  </td>
                  <td className="py-3 pr-4">
                    <RepositoryMetadataCell row={row} />
                  </td>
                  <td className="py-3 pr-4">
                    <Badge variant={row.readiness_checked ? "success" : "outline"}>
                      {row.readiness_checked ? "Checked" : "Pending"}
                    </Badge>
                  </td>
                  <td className="py-3">
                    <RepositorySyncCell row={row} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

function WorkflowProfileCoverageTable({ rows }: { rows: WorkflowProfileCoverageRow[] }) {
  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">No workflow coverage data yet.</p>
  }

  return (
    <Card>
      <CardHeader className="pb-4">
        <CardTitle>Workflow Coverage</CardTitle>
        <p className="text-sm text-muted-foreground">
          Coverage shows how many sessions per agent currently have a derived workflow profile.
        </p>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="text-left text-muted-foreground">
              <tr className="border-b border-border/60">
                <th className="pb-3 pr-4 font-medium">Agent</th>
                <th className="pb-3 pr-4 font-medium">Sessions</th>
                <th className="pb-3 pr-4 font-medium">Profiles</th>
                <th className="pb-3 font-medium">Coverage</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.agent_type} className="border-b border-border/40 last:border-b-0">
                  <td className="py-3 pr-4 font-medium">{row.agent_type}</td>
                  <td className="py-3 pr-4 text-muted-foreground">
                    {formatNumber(row.session_count)}
                  </td>
                  <td className="py-3 pr-4 text-muted-foreground">
                    {formatNumber(row.sessions_with_workflow_profiles)}
                  </td>
                  <td className="py-3 font-medium">
                    {formatCoverage(row.workflow_profile_coverage_pct)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

function githubSyncSubtitle(integrity: MeasurementIntegrityStats): string {
  if (integrity.sessions_with_commit_sync_target === 0) {
    return "No repo-linked commit sessions yet"
  }

  return `${formatNumber(integrity.sessions_with_linked_pull_requests)} of ${formatNumber(integrity.sessions_with_commit_sync_target)} repo-linked commit sessions`
}

function repositoryMetadataSubtitle(integrity: MeasurementIntegrityStats): string {
  if (integrity.repositories_in_scope === 0) {
    return "No linked repositories yet"
  }

  return `${formatNumber(integrity.repositories_with_complete_metadata)} of ${formatNumber(integrity.repositories_in_scope)} linked repositories complete`
}

function workflowCoverageSubtitle(integrity: MeasurementIntegrityStats): string {
  return `${formatNumber(integrity.sessions_with_workflow_profiles)} of ${formatNumber(integrity.total_sessions)} sessions`
}

function backfillSummaryLabel(result: {
  sessions_scanned: number
  profiles_created: number
  profiles_updated: number
  profiles_deleted: number
  sessions_unchanged: number
  sessions_skipped: number
}) {
  return [
    `${formatNumber(result.sessions_scanned)} scanned`,
    `${formatNumber(result.profiles_created)} created`,
    `${formatNumber(result.profiles_updated)} updated`,
    `${formatNumber(result.profiles_deleted)} deleted`,
    `${formatNumber(result.sessions_unchanged)} unchanged`,
    `${formatNumber(result.sessions_skipped)} skipped`,
  ].join(" · ")
}

export function AdminSystemTab() {
  const { data: stats, isLoading: isSystemLoading } = useSystemStats()
  const { data: integrity, isLoading: isIntegrityLoading } = useMeasurementIntegrity()
  const workflowBackfill = useBackfillWorkflowProfiles()

  if (isSystemLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 5 }).map((_, i) => <CardSkeleton key={i} />)}
      </div>
    )
  }

  if (!stats) return null

  return (
    <div className="space-y-6">
      <section className="space-y-4">
        <h3 className="text-lg font-semibold">System</h3>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <StatCard
            label="Total Engineers"
            value={formatNumber(stats.total_engineers)}
            subtitle={`${formatNumber(stats.active_engineers)} active`}
            icon={Users}
          />
          <StatCard
            label="Teams"
            value={formatNumber(stats.total_teams)}
            icon={FolderKanban}
          />
          <StatCard
            label="Total Sessions"
            value={formatNumber(stats.total_sessions)}
            icon={MonitorDot}
          />
          <StatCard
            label="Ingest Events"
            value={formatNumber(stats.total_ingest_events)}
            icon={FileInput}
          />
          <StatCard
            label="Database"
            value={stats.database_type}
            icon={Database}
          />
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="text-lg font-semibold">Measurement Integrity</h3>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={workflowBackfill.isPending}
              onClick={() => workflowBackfill.mutate({ limit: 5000, recompute: false, dryRun: false })}
            >
              <RefreshCcw className="mr-2 h-4 w-4" />
              Backfill Workflow Profiles
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={workflowBackfill.isPending}
              onClick={() => workflowBackfill.mutate({ limit: 5000, recompute: true, dryRun: false })}
            >
              <RefreshCcw className="mr-2 h-4 w-4" />
              Recompute Workflow Profiles
            </Button>
          </div>
        </div>
        {workflowBackfill.data && (
          <p className="text-sm text-muted-foreground">
            Workflow profile backfill completed: {backfillSummaryLabel(workflowBackfill.data)}
          </p>
        )}
        {workflowBackfill.error && (
          <p className="text-sm text-destructive">
            Failed to update workflow profiles. Please try again.
          </p>
        )}
        {isIntegrityLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            {Array.from({ length: 6 }).map((_, i) => <CardSkeleton key={i} />)}
          </div>
        ) : integrity ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            <StatCard
              label="Facet Extraction"
              value={formatCoverage(integrity.facet_coverage_pct)}
              subtitle={`${formatNumber(integrity.sessions_with_facets)} of ${formatNumber(integrity.total_sessions)} sessions`}
              icon={CheckCircle2}
            />
            <StatCard
              label="Transcript Completeness"
              value={formatCoverage(integrity.transcript_coverage_pct)}
              subtitle={`${formatNumber(integrity.sessions_with_messages)} of ${formatNumber(integrity.total_sessions)} sessions`}
              icon={FileText}
            />
            <StatCard
              label="Workflow Profiles"
              value={formatCoverage(integrity.workflow_profile_coverage_pct)}
              subtitle={workflowCoverageSubtitle(integrity)}
              icon={RefreshCcw}
            />
            <StatCard
              label="GitHub Sync"
              value={formatCoverage(integrity.github_sync_coverage_pct)}
              subtitle={githubSyncSubtitle(integrity)}
              icon={GitPullRequest}
            />
            <StatCard
              label="Repository Metadata"
              value={formatCoverage(integrity.repository_metadata_coverage_pct)}
              subtitle={repositoryMetadataSubtitle(integrity)}
              icon={FolderGit2}
            />
            <StatCard
              label="Low-Confidence Sessions"
              value={formatNumber(integrity.low_confidence_sessions)}
              subtitle="Confidence score below 0.70"
              icon={AlertTriangle}
            />
            <StatCard
              label="Remaining Legacy Rows"
              value={formatNumber(integrity.remaining_legacy_rows)}
              subtitle={`${formatNumber(integrity.legacy_outcome_sessions)} outcome rows, ${formatNumber(integrity.legacy_goal_category_sessions)} goal-category rows`}
              icon={RefreshCcw}
            />
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">Measurement integrity data is unavailable.</p>
        )}
        {!isIntegrityLoading && integrity && <SourceQualityTable rows={integrity.source_quality} />}
        {!isIntegrityLoading && integrity && (
          <WorkflowProfileCoverageTable rows={integrity.workflow_profile_quality} />
        )}
        {!isIntegrityLoading && integrity && (
          <RepositoryQualityTable rows={integrity.repository_quality} />
        )}
      </section>
    </div>
  )
}
