import { BarChart3, Sparkles, Users } from "lucide-react"
import { StatCard } from "@/components/dashboard/stat-card"
import { formatNumber, formatPercent } from "@/lib/utils"
import type { MaturityAnalyticsResponse } from "@/types/api"

interface MaturitySummaryProps {
  data: MaturityAnalyticsResponse
}

export function MaturitySummary({ data }: MaturitySummaryProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <StatCard
        label="Avg Leverage Score"
        value={data.avg_leverage_score.toFixed(1)}
        subtitle="0-100 composite score"
        icon={Sparkles}
      />
      <StatCard
        label="Orchestration Adoption"
        value={formatPercent(data.orchestration_adoption_rate)}
        subtitle="Engineers using agents/skills"
        icon={Users}
      />
      <StatCard
        label="Sessions Analyzed"
        value={formatNumber(data.sessions_analyzed)}
        icon={BarChart3}
      />
    </div>
  )
}
