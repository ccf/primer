import { Link } from "react-router-dom"
import { Activity, CheckCircle2, DollarSign, MessageSquare, ArrowLeft } from "lucide-react"
import {
  useTeam,
  useOverview,
  useEngineerAnalytics,
  useDailyStats,
  useToolRankings,
} from "@/hooks/use-api-queries"
import { StatCard } from "@/components/dashboard/stat-card"
import { DailyActivityChart } from "@/components/dashboard/daily-activity-chart"
import { ToolRankingChart } from "@/components/dashboard/tool-ranking-chart"
import { CardSkeleton, ChartSkeleton } from "@/components/shared/loading-skeleton"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatNumber, formatTokens, formatDuration, formatCost, formatPercent } from "@/lib/utils"
import type { DateRange } from "@/components/layout/date-range-picker"

interface TeamDetailPageProps {
  teamId: string
  dateRange: DateRange | null
}

export function TeamDetailPage({ teamId, dateRange }: TeamDetailPageProps) {
  const startDate = dateRange?.startDate
  const endDate = dateRange?.endDate

  const { data: team, isLoading: loadingTeam } = useTeam(teamId)
  const { data: overview, isLoading: loadingOverview } = useOverview(teamId, startDate, endDate)
  const { data: engineers, isLoading: loadingEngineers } = useEngineerAnalytics(
    teamId,
    startDate,
    endDate,
  )
  const { data: daily, isLoading: loadingDaily } = useDailyStats(teamId, 30, startDate, endDate)
  const { data: tools, isLoading: loadingTools } = useToolRankings(teamId, startDate, endDate)

  if (loadingTeam || loadingOverview) {
    return (
      <div className="space-y-6">
        <CardSkeleton />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
        <ChartSkeleton />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link
          to="/teams"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Teams
        </Link>
      </div>

      <h1 className="text-2xl font-bold">{team?.name ?? "Team"}</h1>

      {overview && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            label="Sessions"
            value={formatNumber(overview.total_sessions)}
            icon={Activity}
          />
          <StatCard
            label="Messages"
            value={formatNumber(overview.total_messages)}
            icon={MessageSquare}
          />
          <StatCard
            label="Success Rate"
            value={formatPercent(overview.success_rate)}
            icon={CheckCircle2}
          />
          <StatCard
            label="Estimated Cost"
            value={overview.estimated_cost != null ? formatCost(overview.estimated_cost) : "-"}
            icon={DollarSign}
          />
        </div>
      )}

      {loadingDaily ? <ChartSkeleton /> : daily && <DailyActivityChart data={daily} />}

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Engineer Leaderboard */}
        {loadingEngineers ? (
          <ChartSkeleton />
        ) : (
          engineers &&
          engineers.engineers.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Engineer Leaderboard</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border">
                        <th className="pb-2 text-left font-medium text-muted-foreground">
                          Engineer
                        </th>
                        <th className="pb-2 text-right font-medium text-muted-foreground">
                          Sessions
                        </th>
                        <th className="pb-2 text-right font-medium text-muted-foreground">
                          Tokens
                        </th>
                        <th className="pb-2 text-right font-medium text-muted-foreground">
                          Success
                        </th>
                        <th className="pb-2 text-right font-medium text-muted-foreground">
                          Avg Duration
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {engineers.engineers.map((eng) => (
                        <tr key={eng.engineer_id} className="border-b border-border last:border-0">
                          <td className="py-2">
                            <div className="flex items-center gap-2">
                              {eng.avatar_url ? (
                                <img
                                  src={eng.avatar_url}
                                  alt={eng.name}
                                  className="h-6 w-6 rounded-full"
                                />
                              ) : (
                                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-muted text-xs">
                                  {eng.name.charAt(0)}
                                </div>
                              )}
                              {eng.name}
                            </div>
                          </td>
                          <td className="py-2 text-right">{eng.total_sessions}</td>
                          <td className="py-2 text-right">{formatTokens(eng.total_tokens)}</td>
                          <td className="py-2 text-right">{formatPercent(eng.success_rate)}</td>
                          <td className="py-2 text-right">{formatDuration(eng.avg_duration)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )
        )}

        {/* Top Tools */}
        {loadingTools ? <ChartSkeleton /> : tools && <ToolRankingChart data={tools} />}
      </div>
    </div>
  )
}
