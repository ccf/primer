import { Link } from "react-router-dom"
import { DollarSign } from "lucide-react"
import {
  useDailyStats,
  useToolRankings,
  useModelRankings,
  useRecommendations,
  useActivityHeatmap,
  useProductivity,
} from "@/hooks/use-api-queries"
import { DailyActivityChart } from "@/components/dashboard/daily-activity-chart"
import { ActivityHeatmap } from "@/components/dashboard/activity-heatmap"
import { OutcomeChart } from "@/components/dashboard/outcome-chart"
import { SessionTypeChart } from "@/components/dashboard/session-type-chart"
import { ToolRankingChart } from "@/components/dashboard/tool-ranking-chart"
import { ModelUsageChart } from "@/components/dashboard/model-usage-chart"
import { ProductivitySection } from "@/components/dashboard/productivity-section"
import { RecommendationsPanel } from "@/components/dashboard/recommendations-panel"
import { ChartSkeleton } from "@/components/shared/loading-skeleton"
import { formatCost } from "@/lib/utils"
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
  const { data: heatmap, isLoading: loadingHeatmap } = useActivityHeatmap(teamId, startDate, endDate)
  const { data: productivity, isLoading: loadingProductivity } = useProductivity(teamId, startDate, endDate)

  return (
    <div className="space-y-6">
      {loadingProductivity ? <ChartSkeleton /> : productivity && <ProductivitySection data={productivity} />}

      {loadingDaily ? <ChartSkeleton /> : daily && <DailyActivityChart data={daily} />}

      {loadingHeatmap ? <ChartSkeleton /> : heatmap && heatmap.cells.length > 0 && <ActivityHeatmap data={heatmap} />}

      {/* Cost summary with link to FinOps */}
      {overview.estimated_cost != null && overview.estimated_cost > 0 && (
        <Link
          to="/finops"
          className="flex items-center gap-3 rounded-lg border border-border bg-card p-4 transition-colors hover:bg-accent"
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/8">
            <DollarSign className="h-4 w-4 text-primary" />
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium">Estimated Spend: {formatCost(overview.estimated_cost)}</p>
            <p className="text-xs text-muted-foreground">View cost analytics, forecasting, and budgets in FinOps</p>
          </div>
          <span className="text-xs font-medium text-primary">View FinOps →</span>
        </Link>
      )}

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
