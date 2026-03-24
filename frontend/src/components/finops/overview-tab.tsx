import { useCostAnalytics, useProductivity, useQualityMetrics } from "@/hooks/use-api-queries"
import { DailyCostChart } from "@/components/dashboard/daily-cost-chart"
import { CostBreakdownChart } from "@/components/dashboard/cost-breakdown-chart"
import { WorkflowCostTable } from "@/components/finops/workflow-cost-table"
import { WorkflowCompareCard } from "@/components/finops/workflow-compare-card"
import { CardSkeleton, ChartSkeleton } from "@/components/shared/loading-skeleton"
import { SectionHeader } from "@/components/shared/section-header"
import { formatCost, getModelPricing } from "@/lib/utils"

interface OverviewTabProps {
  teamId: string | null
  startDate?: string
  endDate?: string
}

export function OverviewTab({ teamId, startDate, endDate }: OverviewTabProps) {
  const costs = useCostAnalytics(teamId, startDate, endDate)
  const productivity = useProductivity(teamId, startDate, endDate)
  const quality = useQualityMetrics(teamId, startDate, endDate)

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
      <SectionHeader
        title="Financial snapshot"
        description="Quick read on spend, efficiency, and what your workflow mix is doing to cost."
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {kpis.map((kpi) => (
          <div
            key={kpi.label}
            className="rounded-2xl border border-border/70 bg-gradient-to-br from-card via-card to-primary/[0.03] p-5 shadow-sm"
          >
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
              {kpi.label}
            </p>
            <p className="mt-3 font-display text-3xl tracking-tight">{kpi.value}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <DailyCostChart data={costData.daily_costs} />
        <CostBreakdownChart data={costData.model_breakdown} />
      </div>

      <SectionHeader
        title="Workflow economics"
        description="The most important FinOps question is not just what models cost, but which workflows earn their keep."
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
        <WorkflowCostTable rows={costData.workflow_breakdown} />
        <WorkflowCompareCard
          workflowCosts={costData.workflow_breakdown}
          qualityRows={quality.data?.attribution ?? []}
        />
      </div>
    </div>
  )
}
