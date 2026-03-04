import { useSessionInsights } from "@/hooks/use-api-queries"
import { HealthDistributionChart } from "@/components/session-insights/health-distribution-chart"
import { PrimarySuccessChart } from "@/components/session-insights/primary-success-chart"
import { SatisfactionTrendChart } from "@/components/session-insights/satisfaction-trend-chart"
import { DailyHealthTrendChart } from "@/components/session-insights/daily-health-trend-chart"
import { GoalCategoryChart } from "@/components/session-insights/goal-category-chart"
import { GoalTypeTable } from "@/components/session-insights/goal-type-table"
import { EndReasonTable } from "@/components/session-insights/end-reason-table"
import { PermissionModeTable } from "@/components/session-insights/permission-mode-table"
import { FrictionClusterList } from "@/components/session-insights/friction-cluster-list"
import { DailyCacheTrendChart } from "@/components/session-insights/daily-cache-trend-chart"
import { ChartSkeleton } from "@/components/shared/loading-skeleton"

interface InsightsTabProps {
  teamId: string | null
  startDate?: string
  endDate?: string
}

export function InsightsTab({ teamId, startDate, endDate }: InsightsTabProps) {
  const { data, isLoading } = useSessionInsights(teamId, startDate, endDate)

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-6 lg:grid-cols-2">
          <ChartSkeleton />
          <ChartSkeleton />
        </div>
        <div className="grid gap-6 lg:grid-cols-2">
          <ChartSkeleton />
          <ChartSkeleton />
        </div>
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-2">
        <HealthDistributionChart data={data.health_distribution} />
        <PrimarySuccessChart data={data.primary_success} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <SatisfactionTrendChart data={data.satisfaction.trend} />
        <DailyHealthTrendChart data={data.health_distribution.daily_trend} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <GoalCategoryChart data={data.goals.goal_category_breakdown} />
        <GoalTypeTable data={data.goals.session_type_breakdown} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <EndReasonTable data={data.end_reasons} />
        <PermissionModeTable data={data.permission_modes} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <FrictionClusterList data={data.friction_clusters} />
        <DailyCacheTrendChart data={data.cache_efficiency.daily_cache_trend} />
      </div>
    </div>
  )
}
