import {
  useDailyStats,
  useToolRankings,
  useModelRankings,
  useRecommendations,
  useCostAnalytics,
  useActivityHeatmap,
  useProductivity,
} from "@/hooks/use-api-queries"
import { DailyActivityChart } from "@/components/dashboard/daily-activity-chart"
import { ActivityHeatmap } from "@/components/dashboard/activity-heatmap"
import { DailyCostChart } from "@/components/dashboard/daily-cost-chart"
import { CostBreakdownChart } from "@/components/dashboard/cost-breakdown-chart"
import { OutcomeChart } from "@/components/dashboard/outcome-chart"
import { SessionTypeChart } from "@/components/dashboard/session-type-chart"
import { ToolRankingChart } from "@/components/dashboard/tool-ranking-chart"
import { ModelUsageChart } from "@/components/dashboard/model-usage-chart"
import { ProductivitySection } from "@/components/dashboard/productivity-section"
import { RecommendationsPanel } from "@/components/dashboard/recommendations-panel"
import { ChartSkeleton } from "@/components/shared/loading-skeleton"
import type { OverviewStats } from "@/types/api"

interface OverviewTabProps {
  overview: OverviewStats
  teamId: string | null
  startDate?: string
  endDate?: string
}

export function OverviewTab({ overview, teamId, startDate, endDate }: OverviewTabProps) {
  const { data: daily, isLoading: loadingDaily } = useDailyStats(teamId, 30, startDate, endDate)
  const { data: tools, isLoading: loadingTools } = useToolRankings(teamId, startDate, endDate)
  const { data: models, isLoading: loadingModels } = useModelRankings(teamId, startDate, endDate)
  const { data: recs, isLoading: loadingRecs } = useRecommendations(teamId, startDate, endDate)
  const { data: costs, isLoading: loadingCosts } = useCostAnalytics(teamId, startDate, endDate)
  const { data: heatmap, isLoading: loadingHeatmap } = useActivityHeatmap(teamId, startDate, endDate)
  const { data: productivity, isLoading: loadingProductivity } = useProductivity(teamId, startDate, endDate)

  return (
    <div className="space-y-6">
      {loadingProductivity ? <ChartSkeleton /> : productivity && <ProductivitySection data={productivity} />}

      {loadingDaily ? <ChartSkeleton /> : daily && <DailyActivityChart data={daily} />}

      {loadingHeatmap ? <ChartSkeleton /> : heatmap && heatmap.cells.length > 0 && <ActivityHeatmap data={heatmap} />}

      <div className="grid gap-4 lg:grid-cols-2">
        {loadingCosts ? (
          <ChartSkeleton />
        ) : (
          costs && costs.daily_costs.length > 0 && <DailyCostChart data={costs.daily_costs} />
        )}
        {loadingCosts ? (
          <ChartSkeleton />
        ) : (
          costs && costs.model_breakdown.length > 0 && <CostBreakdownChart data={costs.model_breakdown} />
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <OutcomeChart data={overview.outcome_counts} />
        <SessionTypeChart data={overview.session_type_counts} />
        {loadingTools ? <ChartSkeleton /> : tools && <ToolRankingChart data={tools} />}
        {loadingModels ? <ChartSkeleton /> : models && <ModelUsageChart data={models} />}
      </div>

      {loadingRecs ? <ChartSkeleton /> : recs && <RecommendationsPanel data={recs} />}
    </div>
  )
}
