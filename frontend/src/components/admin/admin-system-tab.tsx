import {
  AlertTriangle,
  CheckCircle2,
  Database,
  FileInput,
  FileText,
  FolderKanban,
  MonitorDot,
  RefreshCcw,
  Users,
} from "lucide-react"
import { useMeasurementIntegrity, useSystemStats } from "@/hooks/use-api-queries"
import { StatCard } from "@/components/dashboard/stat-card"
import { formatNumber } from "@/lib/utils"
import { CardSkeleton } from "@/components/shared/loading-skeleton"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { AgentSourceQuality, TelemetryParity } from "@/types/api"

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
  return (
    <div className="space-y-1">
      <Badge variant={parityVariant(parity)}>{parityLabel(parity)}</Badge>
      <div className="text-xs text-muted-foreground">
        {parity === "unavailable" || coverage == null ? "Not expected" : formatCoverage(coverage)}
      </div>
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

export function AdminSystemTab() {
  const { data: stats, isLoading: isSystemLoading } = useSystemStats()
  const { data: integrity, isLoading: isIntegrityLoading } = useMeasurementIntegrity()

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
        <h3 className="text-lg font-semibold">Measurement Integrity</h3>
        {isIntegrityLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} />)}
          </div>
        ) : integrity ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Facet Coverage"
              value={formatCoverage(integrity.facet_coverage_pct)}
              subtitle={`${formatNumber(integrity.sessions_with_facets)} of ${formatNumber(integrity.total_sessions)} sessions`}
              icon={CheckCircle2}
            />
            <StatCard
              label="Transcript Coverage"
              value={formatCoverage(integrity.transcript_coverage_pct)}
              subtitle={`${formatNumber(integrity.sessions_with_messages)} of ${formatNumber(integrity.total_sessions)} sessions`}
              icon={FileText}
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
      </section>
    </div>
  )
}
