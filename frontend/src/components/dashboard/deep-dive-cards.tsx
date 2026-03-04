import { Link } from "react-router-dom"
import { DollarSign, TrendingUp, GitPullRequest, Sparkles, ArrowRight } from "lucide-react"
import { useProductivity, useMaturityAnalytics, useQualityMetrics } from "@/hooks/use-api-queries"
import { formatCost, formatPercent } from "@/lib/utils"
import type { LucideIcon } from "lucide-react"

interface DeepDiveCardProps {
  to: string
  icon: LucideIcon
  title: string
  metrics: { label: string; value: string }[]
  iconColor: string
  iconBg: string
}

function DeepDiveCard({ to, icon: Icon, title, metrics, iconColor, iconBg }: DeepDiveCardProps) {
  return (
    <Link
      to={to}
      className="group flex items-center gap-3 rounded-xl border border-border bg-card px-4 py-3 transition-colors hover:border-primary/30 hover:bg-accent/50"
    >
      <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${iconBg}`}>
        <Icon className={`h-4 w-4 ${iconColor}`} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium text-muted-foreground">{title}</p>
        <div className="flex items-baseline gap-3">
          {metrics.map((m) => (
            <div key={m.label} className="flex items-baseline gap-1">
              <span className="text-base font-display">{m.value}</span>
              <span className="text-[10px] text-muted-foreground">{m.label}</span>
            </div>
          ))}
        </div>
      </div>
      <ArrowRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground/40 transition-all group-hover:translate-x-0.5 group-hover:text-primary" />
    </Link>
  )
}

interface DeepDiveCardsProps {
  teamId: string | null
  startDate?: string
  endDate?: string
}

export function DeepDiveCards({ teamId, startDate, endDate }: DeepDiveCardsProps) {
  const { data: prod } = useProductivity(teamId, startDate, endDate)
  const { data: maturity } = useMaturityAnalytics(teamId, startDate, endDate)
  const { data: quality } = useQualityMetrics(teamId, startDate, endDate)

  return (
    <div className="space-y-2">
      <h2 className="text-sm font-semibold text-muted-foreground">Deep Dive</h2>
      <div className="grid gap-4 sm:grid-cols-2">
        <DeepDiveCard
          to="/finops"
          icon={DollarSign}
          title="FinOps"
          iconColor="text-emerald-600 dark:text-emerald-400"
          iconBg="bg-emerald-500/10"
          metrics={[
            { label: "Total Spend", value: prod ? formatCost(prod.total_cost) : "-" },
            {
              label: "ROI",
              value: prod?.roi_ratio != null ? `${prod.roi_ratio.toFixed(1)}x` : "-",
            },
          ]}
        />
        <DeepDiveCard
          to="/maturity"
          icon={TrendingUp}
          title="AI Maturity"
          iconColor="text-blue-600 dark:text-blue-400"
          iconBg="bg-blue-500/10"
          metrics={[
            { label: "Adoption", value: prod ? `${prod.adoption_rate.toFixed(0)}%` : "-" },
            {
              label: "Avg Leverage",
              value:
                maturity?.avg_leverage_score != null
                  ? maturity.avg_leverage_score.toFixed(1)
                  : "-",
            },
          ]}
        />
        <DeepDiveCard
          to="/sessions"
          icon={GitPullRequest}
          title="Quality"
          iconColor="text-violet-600 dark:text-violet-400"
          iconBg="bg-violet-500/10"
          metrics={[
            {
              label: "PRs Tracked",
              value:
                quality?.overview.total_prs != null ? String(quality.overview.total_prs) : "-",
            },
            {
              label: "Merge Rate",
              value:
                quality?.overview.pr_merge_rate != null
                  ? formatPercent(quality.overview.pr_merge_rate)
                  : "-",
            },
          ]}
        />
        <DeepDiveCard
          to="/synthesis"
          icon={Sparkles}
          title="Synthesis"
          iconColor="text-amber-600 dark:text-amber-400"
          iconBg="bg-amber-500/10"
          metrics={[
            { label: "Engineers", value: prod ? String(prod.total_engineers_in_scope) : "-" },
            { label: "Power Users", value: prod ? String(prod.power_users) : "-" },
          ]}
        />
      </div>
    </div>
  )
}
