import { useBottleneckAnalytics, useToolAdoption, useSkillInventory } from "@/hooks/use-api-queries"
import { BottleneckSummary } from "@/components/bottlenecks/bottleneck-summary"
import { FrictionTrendChart } from "@/components/bottlenecks/friction-trend-chart"
import { ToolAdoptionSummary } from "@/components/tools/tool-adoption-summary"
import { ToolAdoptionChart } from "@/components/tools/tool-adoption-chart"
import { TeamSkillGaps } from "@/components/insights/team-skill-gaps"
import { ChartSkeleton, CardSkeleton } from "@/components/shared/loading-skeleton"

interface InsightsTabProps {
  teamId: string | null
  startDate?: string
  endDate?: string
}

export function InsightsTab({ teamId, startDate, endDate }: InsightsTabProps) {
  const { data: bottlenecks, isLoading: loadingBottlenecks } = useBottleneckAnalytics(teamId, startDate, endDate)
  const { data: toolData, isLoading: loadingTools } = useToolAdoption(teamId, startDate, endDate)
  const { data: skills, isLoading: loadingSkills } = useSkillInventory(teamId, startDate, endDate)

  return (
    <div className="space-y-6">
      {loadingBottlenecks ? (
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <CardSkeleton key={i} />
            ))}
          </div>
          <ChartSkeleton />
        </div>
      ) : bottlenecks && bottlenecks.total_sessions_analyzed > 0 ? (
        <>
          <BottleneckSummary data={bottlenecks} />
          <FrictionTrendChart data={bottlenecks.friction_trends} />
        </>
      ) : null}

      {loadingTools ? (
        <ChartSkeleton />
      ) : toolData && toolData.total_engineers > 0 ? (
        <>
          <ToolAdoptionSummary data={toolData} />
          <ToolAdoptionChart data={toolData.tool_adoption} />
        </>
      ) : null}

      {loadingSkills ? (
        <CardSkeleton />
      ) : skills && skills.team_skill_gaps.length > 0 ? (
        <TeamSkillGaps data={skills.team_skill_gaps} />
      ) : null}
    </div>
  )
}
