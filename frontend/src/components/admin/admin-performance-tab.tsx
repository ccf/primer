import { Activity, DollarSign, GitPullRequest, Sparkles, Target, TrendingUp } from "lucide-react"
import {
  useCostAnalytics,
  useMaturityAnalytics,
  useProductivity,
  useQualityMetrics,
} from "@/hooks/use-api-queries"
import { StatCard } from "@/components/dashboard/stat-card"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { CardSkeleton } from "@/components/shared/loading-skeleton"
import { formatCost, formatPercent } from "@/lib/utils"

interface AdminPerformanceTabProps {
  teamId: string | null
  startDate?: string
  endDate?: string
}

export function AdminPerformanceTab({
  teamId,
  startDate,
  endDate,
}: AdminPerformanceTabProps) {
  const { data: productivity, isLoading: loadingProductivity } = useProductivity(
    teamId,
    startDate,
    endDate,
  )
  const { data: quality, isLoading: loadingQuality } = useQualityMetrics(
    teamId,
    startDate,
    endDate,
  )
  const { data: cost, isLoading: loadingCost } = useCostAnalytics(teamId, startDate, endDate)
  const { data: maturity, isLoading: loadingMaturity } = useMaturityAnalytics(
    teamId,
    startDate,
    endDate,
  )

  if (loadingProductivity || loadingQuality || loadingCost || loadingMaturity) {
    return (
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <CardSkeleton key={i} />
        ))}
      </div>
    )
  }

  if (!productivity || !quality || !cost || !maturity) return null

  const topWorkflow = cost.workflow_breakdown[0]

  return (
    <div className="space-y-6">
      <section className="space-y-4">
        <h3 className="text-lg font-semibold">Leadership Performance</h3>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <StatCard
            label="Sessions / Engineer / Day"
            value={productivity.sessions_per_engineer_per_day.toFixed(1)}
            icon={Activity}
          />
          <StatCard
            label="Adoption"
            value={formatPercent(productivity.adoption_rate / 100)}
            subtitle={`${productivity.power_users} power users`}
            icon={Target}
          />
          <StatCard
            label="Total Spend"
            value={formatCost(productivity.total_cost)}
            subtitle={
              productivity.cost_per_successful_outcome != null
                ? `${formatCost(productivity.cost_per_successful_outcome)} / success`
                : undefined
            }
            icon={DollarSign}
          />
          <StatCard
            label="Merge Rate"
            value={formatPercent(quality.overview.pr_merge_rate)}
            subtitle={`${quality.overview.total_prs} PRs tracked`}
            icon={GitPullRequest}
          />
          <StatCard
            label="Avg Leverage"
            value={maturity.avg_leverage_score.toFixed(1)}
            subtitle={formatPercent(maturity.orchestration_adoption_rate)}
            icon={TrendingUp}
          />
          <StatCard
            label="Customization Adoption"
            value={formatPercent(maturity.explicit_customization_adoption_rate)}
            subtitle={formatPercent(maturity.team_orchestration_adoption_rate)}
            icon={Sparkles}
          />
        </div>
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Quality & Delivery</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>
              {quality.overview.total_prs} PRs tracked with{" "}
              <span className="font-medium text-foreground">
                {formatPercent(quality.overview.pr_merge_rate)}
              </span>{" "}
              merge rate.
            </p>
            <p>
              Findings fix rate:{" "}
              <span className="font-medium text-foreground">
                {formatPercent(quality.findings_overview?.fix_rate)}
              </span>
            </p>
            <p>
              Avg time to merge:{" "}
              <span className="font-medium text-foreground">
                {quality.overview.avg_time_to_merge_hours != null
                  ? `${quality.overview.avg_time_to_merge_hours.toFixed(1)}h`
                  : "-"}
              </span>
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Cost & Adoption</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>
              Avg cost per session:{" "}
              <span className="font-medium text-foreground">
                {productivity.avg_cost_per_session != null
                  ? formatCost(productivity.avg_cost_per_session)
                  : "-"}
              </span>
            </p>
            <p>
              Top workflow spend slice:{" "}
              <span className="font-medium text-foreground">
                {topWorkflow
                  ? `${topWorkflow.label} (${formatCost(topWorkflow.total_estimated_cost)})`
                  : "-"}
              </span>
            </p>
            <p>
              Team orchestration adoption:{" "}
              <span className="font-medium text-foreground">
                {formatPercent(maturity.team_orchestration_adoption_rate)}
              </span>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
