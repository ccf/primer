import { BarChart3, Sparkles, Target, Users } from "lucide-react"
import { StatCard } from "@/components/dashboard/stat-card"
import { formatNumber, formatPercent } from "@/lib/utils"
import type { MaturityAnalyticsResponse } from "@/types/api"

interface MaturitySummaryProps {
  data: MaturityAnalyticsResponse
}

export function MaturitySummary({ data }: MaturitySummaryProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      <StatCard
        label="Avg Leverage Score"
        value={data.avg_leverage_score.toFixed(1)}
        subtitle="0-100 composite score"
        icon={Sparkles}
      />
      <StatCard
        label="Avg Effectiveness"
        value={data.avg_effectiveness_score != null ? data.avg_effectiveness_score.toFixed(1) : "N/A"}
        subtitle="Success, quality, follow-through, and cost"
        icon={Target}
      />
      <StatCard
        label="Orchestration Adoption"
        value={formatPercent(data.orchestration_adoption_rate)}
        subtitle="Engineers using agents/skills"
        icon={Users}
      />
      <StatCard
        label="Explicit Customization Adoption"
        value={formatPercent(data.explicit_customization_adoption_rate)}
        subtitle="Engineers using explicit MCPs, skills, or subagents"
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
