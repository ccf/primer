import {
  Activity,
  BadgeCheck,
  BarChart3,
  CircleDollarSign,
  ShieldCheck,
} from "lucide-react"
import { StatCard } from "@/components/dashboard/stat-card"
import { formatCost, formatPercent } from "@/lib/utils"
import type { ProjectScorecard as ProjectScorecardData, ProjectWorkspaceResponse } from "@/types/api"

interface ProjectScorecardProps {
  scorecard: ProjectScorecardData
  overview: ProjectWorkspaceResponse["overview"]
}

export function ProjectScorecard({ scorecard, overview }: ProjectScorecardProps) {
  const costValue =
    scorecard.cost_per_successful_outcome != null
      ? formatCost(scorecard.cost_per_successful_outcome)
      : scorecard.avg_cost_per_session != null
        ? formatCost(scorecard.avg_cost_per_session)
        : "-"
  const costSubtitle =
    scorecard.cost_per_successful_outcome != null
      ? "Cost per successful outcome"
      : "Average cost per session"

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
      <StatCard
        label="Adoption"
        value={formatPercent(scorecard.adoption_rate)}
        subtitle={`${overview.total_engineers} engineers active on this project`}
        icon={Activity}
      />
      <StatCard
        label="Effectiveness"
        value={formatPercent(scorecard.effectiveness_rate)}
        subtitle="Successful outcomes across facet-capable sessions"
        icon={BadgeCheck}
      />
      <StatCard
        label="Quality"
        value={formatPercent(scorecard.quality_rate)}
        subtitle="Project-linked PR quality signal"
        icon={BarChart3}
      />
      <StatCard
        label="Cost Efficiency"
        value={costValue}
        subtitle={costSubtitle}
        icon={CircleDollarSign}
      />
      <StatCard
        label="Measurement Confidence"
        value={formatPercent(scorecard.measurement_confidence)}
        subtitle="Telemetry coverage across expected project signals"
        icon={ShieldCheck}
      />
    </div>
  )
}
