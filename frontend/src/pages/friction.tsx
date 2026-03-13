import { useBottleneckAnalytics } from "@/hooks/use-api-queries"
import { PageHeader } from "@/components/shared/page-header"
import { BottleneckSummary } from "@/components/bottlenecks/bottleneck-summary"
import { FrictionTrendChart } from "@/components/bottlenecks/friction-trend-chart"
import { FrictionImpactTable } from "@/components/bottlenecks/friction-impact-table"
import { ProjectFrictionTable } from "@/components/bottlenecks/project-friction-table"
import { RootCauseClusterList } from "@/components/bottlenecks/root-cause-cluster-list"
import { RecoveryPatternList } from "@/components/bottlenecks/recovery-pattern-list"
import { CardSkeleton, ChartSkeleton } from "@/components/shared/loading-skeleton"
import { AlertTriangle } from "lucide-react"
import type { DateRange } from "@/components/layout/date-range-picker"

interface FrictionPageProps {
  teamId: string | null
  dateRange: DateRange | null
}

export function FrictionPage({ teamId, dateRange }: FrictionPageProps) {
  const startDate = dateRange?.startDate
  const endDate = dateRange?.endDate
  const { data, isLoading } = useBottleneckAnalytics(teamId, startDate, endDate)

  if (isLoading) {
    return (
      <div className="space-y-6">
        <CardSkeleton />
        <div className="grid gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
        <ChartSkeleton />
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="space-y-8">
      <PageHeader
        icon={AlertTriangle}
        title="Friction Intelligence"
        description="What's blocking your engineers and how much it costs"
      />

      <BottleneckSummary data={data} />

      <div className="grid gap-6 lg:grid-cols-2">
        <FrictionTrendChart data={data.friction_trends} />
        <FrictionImpactTable data={data.friction_impacts} />
      </div>

      <RootCauseClusterList data={data.root_cause_clusters} />

      <RecoveryPatternList
        overview={data.recovery_overview}
        patterns={data.recovery_patterns}
      />

      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-muted-foreground">By Project</h2>
        <ProjectFrictionTable data={data.project_friction} />
      </section>
    </div>
  )
}
