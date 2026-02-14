import { Database, Users, FolderKanban, MonitorDot, FileInput } from "lucide-react"
import { useSystemStats } from "@/hooks/use-api-queries"
import { StatCard } from "@/components/dashboard/stat-card"
import { formatNumber } from "@/lib/utils"
import { CardSkeleton } from "@/components/shared/loading-skeleton"

export function AdminSystemTab() {
  const { data: stats, isLoading } = useSystemStats()

  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => <CardSkeleton key={i} />)}
      </div>
    )
  }

  if (!stats) return null

  return (
    <div className="space-y-4">
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
    </div>
  )
}
