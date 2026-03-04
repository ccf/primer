import { useCostAnalytics, useProductivity } from "@/hooks/use-api-queries"
import { DailyCostChart } from "@/components/dashboard/daily-cost-chart"
import { CostBreakdownChart } from "@/components/dashboard/cost-breakdown-chart"
import { CardSkeleton, ChartSkeleton } from "@/components/shared/loading-skeleton"
import { formatCost, getModelPricing } from "@/lib/utils"

interface OverviewTabProps {
  teamId: string | null
  startDate?: string
  endDate?: string
}

export function OverviewTab({ teamId, startDate, endDate }: OverviewTabProps) {
  const costs = useCostAnalytics(teamId, startDate, endDate)
  const productivity = useProductivity(teamId, startDate, endDate)

  if (costs.isLoading || productivity.isLoading) {
    return (
      <div className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
        <ChartSkeleton />
        <ChartSkeleton />
      </div>
    )
  }

  if (!costs.data || !productivity.data) return null

  const costData = costs.data
  const prod = productivity.data

  const cacheSavings =
    costData.model_breakdown.reduce((sum, m) => {
      const p = getModelPricing(m.model_name)
      return sum + m.cache_read_tokens * (p.input - p.cacheRead)
    }, 0)

  const kpis = [
    {
      label: "Total Spend",
      value: formatCost(prod.total_cost),
    },
    {
      label: "Avg Cost/Session",
      value: prod.avg_cost_per_session != null ? formatCost(prod.avg_cost_per_session) : "-",
    },
    {
      label: "Cost per Success",
      value:
        prod.cost_per_successful_outcome != null
          ? formatCost(prod.cost_per_successful_outcome)
          : "-",
    },
    {
      label: "Cache Savings",
      value: formatCost(cacheSavings),
    },
  ]

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {kpis.map((kpi) => (
          <div key={kpi.label} className="rounded-lg border border-border bg-card p-4">
            <p className="text-xs font-medium text-muted-foreground">{kpi.label}</p>
            <p className="mt-1 text-2xl font-semibold">{kpi.value}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <DailyCostChart data={costData.daily_costs} />
        <CostBreakdownChart data={costData.model_breakdown} />
      </div>
    </div>
  )
}
