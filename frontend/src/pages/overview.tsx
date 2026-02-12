import { Activity, MessageSquare, Users, Wrench, Zap, FileCode } from "lucide-react"
import { useOverview, useDailyStats, useToolRankings, useModelRankings, useRecommendations } from "@/hooks/use-api-queries"
import { StatCard } from "@/components/dashboard/stat-card"
import { OutcomeChart } from "@/components/dashboard/outcome-chart"
import { SessionTypeChart } from "@/components/dashboard/session-type-chart"
import { DailyActivityChart } from "@/components/dashboard/daily-activity-chart"
import { ToolRankingChart } from "@/components/dashboard/tool-ranking-chart"
import { ModelUsageChart } from "@/components/dashboard/model-usage-chart"
import { RecommendationsPanel } from "@/components/dashboard/recommendations-panel"
import { CardSkeleton, ChartSkeleton } from "@/components/shared/loading-skeleton"
import { formatNumber, formatTokens, formatDuration } from "@/lib/utils"

interface OverviewPageProps {
  teamId: string | null
}

export function OverviewPage({ teamId }: OverviewPageProps) {
  const { data: overview, isLoading: loadingOverview } = useOverview(teamId)
  const { data: daily, isLoading: loadingDaily } = useDailyStats(teamId)
  const { data: tools, isLoading: loadingTools } = useToolRankings(teamId)
  const { data: models, isLoading: loadingModels } = useModelRankings(teamId)
  const { data: recs, isLoading: loadingRecs } = useRecommendations(teamId)

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

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Overview</h1>

      {/* KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Total Sessions"
          value={formatNumber(overview.total_sessions)}
          icon={Activity}
        />
        <StatCard
          label="Engineers"
          value={formatNumber(overview.total_engineers)}
          icon={Users}
        />
        <StatCard
          label="Messages"
          value={formatNumber(overview.total_messages)}
          subtitle={overview.avg_messages_per_session ? `~${overview.avg_messages_per_session.toFixed(1)} per session` : undefined}
          icon={MessageSquare}
        />
        <StatCard
          label="Tool Calls"
          value={formatNumber(overview.total_tool_calls)}
          icon={Wrench}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Input Tokens"
          value={formatTokens(overview.total_input_tokens)}
          icon={FileCode}
        />
        <StatCard
          label="Output Tokens"
          value={formatTokens(overview.total_output_tokens)}
          icon={Zap}
        />
        <StatCard
          label="Avg Duration"
          value={formatDuration(overview.avg_session_duration)}
          icon={Activity}
        />
        <StatCard
          label="Total Tokens"
          value={formatTokens(overview.total_input_tokens + overview.total_output_tokens)}
          icon={FileCode}
        />
      </div>

      {/* Daily Activity */}
      {loadingDaily ? <ChartSkeleton /> : daily && <DailyActivityChart data={daily} />}

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
