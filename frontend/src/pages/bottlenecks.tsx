import { useBottleneckAnalytics } from "@/hooks/use-api-queries"
import { BottleneckSummary } from "@/components/bottlenecks/bottleneck-summary"
import { FrictionTrendChart } from "@/components/bottlenecks/friction-trend-chart"
import { FrictionImpactTable } from "@/components/bottlenecks/friction-impact-table"
import { ProjectFrictionTable } from "@/components/bottlenecks/project-friction-table"
import { CardSkeleton, ChartSkeleton } from "@/components/shared/loading-skeleton"
import { EmptyState } from "@/components/shared/empty-state"
import type { DateRange } from "@/components/layout/date-range-picker"

interface BottlenecksPageProps {
  teamId: string | null
  dateRange: DateRange | null
}

export function BottlenecksPage({ teamId, dateRange }: BottlenecksPageProps) {
  const startDate = dateRange?.startDate
  const endDate = dateRange?.endDate
  const { data, isLoading } = useBottleneckAnalytics(teamId, startDate, endDate)

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Bottlenecks</h1>
        <div className="grid gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
        <ChartSkeleton />
      </div>
    )
  }

  if (!data || data.total_sessions_analyzed === 0) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Bottlenecks</h1>
        <EmptyState message="No session data available for bottleneck analysis" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Bottlenecks</h1>
      <BottleneckSummary data={data} />
      <FrictionTrendChart data={data.friction_trends} />
      <FrictionImpactTable data={data.friction_impacts} />
      <ProjectFrictionTable data={data.project_friction} />
    </div>
  )
}
