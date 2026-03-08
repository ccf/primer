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

function formatCoverage(value: number): string {
  return `${value.toFixed(1)}%`
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
      </section>
    </div>
  )
}
