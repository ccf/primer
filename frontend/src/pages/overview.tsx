import { Activity, CheckCircle2, MessageSquare, Users, Wrench, FileCode, DollarSign, Download } from "lucide-react"
import { useAuth } from "@/lib/auth-context"
import { useOverview, useDailyStats, useToolRankings, useModelRankings, useRecommendations, useCostAnalytics, useActivityHeatmap, useProductivity } from "@/hooks/use-api-queries"
import { Button } from "@/components/ui/button"
import { exportToCsv } from "@/lib/csv-export"
import { StatCard } from "@/components/dashboard/stat-card"
import { OutcomeChart } from "@/components/dashboard/outcome-chart"
import { SessionTypeChart } from "@/components/dashboard/session-type-chart"
import { DailyActivityChart } from "@/components/dashboard/daily-activity-chart"
import { ToolRankingChart } from "@/components/dashboard/tool-ranking-chart"
import { ModelUsageChart } from "@/components/dashboard/model-usage-chart"
import { DailyCostChart } from "@/components/dashboard/daily-cost-chart"
import { CostBreakdownChart } from "@/components/dashboard/cost-breakdown-chart"
import { ActivityHeatmap } from "@/components/dashboard/activity-heatmap"
import { ProductivitySection } from "@/components/dashboard/productivity-section"
import { RecommendationsPanel } from "@/components/dashboard/recommendations-panel"
import { CardSkeleton, ChartSkeleton } from "@/components/shared/loading-skeleton"
import { formatNumber, formatTokens, formatDuration, formatCost, formatPercent } from "@/lib/utils"
import type { DateRange } from "@/components/layout/date-range-picker"

interface OverviewPageProps {
  teamId: string | null
  dateRange: DateRange | null
}

function computeDelta(current: number | null | undefined, previous: number | null | undefined): { value: number } | null {
  if (current == null || previous == null || previous === 0) return null
  return { value: ((current - previous) / previous) * 100 }
}

export function OverviewPage({ teamId, dateRange }: OverviewPageProps) {
  const { user } = useAuth()
  const role = user?.role ?? "admin"

  const startDate = dateRange?.startDate
  const endDate = dateRange?.endDate
  const { data: overview, isLoading: loadingOverview } = useOverview(teamId, startDate, endDate)
  const { data: daily, isLoading: loadingDaily } = useDailyStats(teamId, 30, startDate, endDate)
  const { data: tools, isLoading: loadingTools } = useToolRankings(teamId, startDate, endDate)
  const { data: models, isLoading: loadingModels } = useModelRankings(teamId, startDate, endDate)
  const { data: recs, isLoading: loadingRecs } = useRecommendations(teamId, startDate, endDate)
  const { data: costs, isLoading: loadingCosts } = useCostAnalytics(teamId, startDate, endDate)
  const { data: heatmap, isLoading: loadingHeatmap } = useActivityHeatmap(teamId, startDate, endDate)
  const { data: productivity, isLoading: loadingProductivity } = useProductivity(teamId, startDate, endDate)

  if (loadingOverview) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} />)}
        </div>
        <ChartSkeleton />
      </div>
    )
  }

  if (!overview) return null

  const prev = overview.previous_period

  const handleExport = () => {
    if (!daily) return
    exportToCsv(
      "overview-report.csv",
      ["Date", "Sessions", "Messages", "Tool Calls", "Success Rate"],
      daily.map((d) => [
        d.date,
        d.session_count,
        d.message_count,
        d.tool_call_count,
        d.success_rate != null ? `${(d.success_rate * 100).toFixed(1)}%` : "",
      ]),
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">
          {role === "engineer" ? "My Dashboard" : role === "team_lead" ? "Team Overview" : "Overview"}
        </h1>
        {daily && daily.length > 0 && (
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download className="mr-1 h-4 w-4" />
            Export CSV
          </Button>
        )}
      </div>

      {/* KPI Cards — Row 1 */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Total Sessions"
          value={formatNumber(overview.total_sessions)}
          icon={Activity}
          delta={computeDelta(overview.total_sessions, prev?.total_sessions)}
        />
        <StatCard
          label="Engineers"
          value={formatNumber(overview.total_engineers)}
          icon={Users}
          delta={computeDelta(overview.total_engineers, prev?.total_engineers)}
        />
        <StatCard
          label="Messages"
          value={formatNumber(overview.total_messages)}
          subtitle={overview.avg_messages_per_session ? `~${overview.avg_messages_per_session.toFixed(1)} per session` : undefined}
          icon={MessageSquare}
          delta={computeDelta(overview.total_messages, prev?.total_messages)}
        />
        <StatCard
          label="Estimated Cost"
          value={overview.estimated_cost != null ? formatCost(overview.estimated_cost) : "-"}
          icon={DollarSign}
          delta={computeDelta(overview.estimated_cost, prev?.estimated_cost)}
        />
      </div>

      {/* KPI Cards — Row 2 */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Success Rate"
          value={formatPercent(overview.success_rate)}
          icon={CheckCircle2}
          delta={computeDelta(
            overview.success_rate != null ? overview.success_rate * 100 : null,
            prev?.success_rate != null ? prev.success_rate * 100 : null,
          )}
        />
        <StatCard
          label="Input Tokens"
          value={formatTokens(overview.total_input_tokens)}
          icon={FileCode}
          delta={computeDelta(overview.total_input_tokens, prev?.total_input_tokens)}
        />
        <StatCard
          label="Avg Duration"
          value={formatDuration(overview.avg_session_duration)}
          icon={Activity}
        />
        <StatCard
          label="Tool Calls"
          value={formatNumber(overview.total_tool_calls)}
          icon={Wrench}
          delta={computeDelta(overview.total_tool_calls, prev?.total_tool_calls)}
        />
      </div>

      {/* Productivity / ROI */}
      {(role === "team_lead" || role === "admin") && (
        loadingProductivity ? <ChartSkeleton /> : productivity && <ProductivitySection data={productivity} />
      )}

      {/* Daily Activity */}
      {loadingDaily ? <ChartSkeleton /> : daily && <DailyActivityChart data={daily} />}

      {/* Activity Heatmap */}
      {loadingHeatmap ? <ChartSkeleton /> : heatmap && heatmap.cells.length > 0 && <ActivityHeatmap data={heatmap} />}

      {/* Daily Cost + Cost Breakdown */}
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

      {/* Charts Grid */}
      <div className="grid gap-4 lg:grid-cols-2">
        <OutcomeChart data={overview.outcome_counts} />
        <SessionTypeChart data={overview.session_type_counts} />
        {loadingTools ? <ChartSkeleton /> : tools && <ToolRankingChart data={tools} />}
        {loadingModels ? <ChartSkeleton /> : models && <ModelUsageChart data={models} />}
      </div>

      {/* Recommendations */}
      {loadingRecs ? <ChartSkeleton /> : recs && <RecommendationsPanel data={recs} />}
    </div>
  )
}
