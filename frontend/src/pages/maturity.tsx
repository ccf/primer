import { useState } from "react"
import { useMaturityAnalytics } from "@/hooks/use-api-queries"
import { PageTabs } from "@/components/ui/page-tabs"
import { MaturitySummary } from "@/components/maturity/maturity-summary"
import { ToolCategoryChart } from "@/components/maturity/tool-category-chart"
import { AgentSkillTable } from "@/components/maturity/agent-skill-table"
import { LeverageScoreTable } from "@/components/maturity/leverage-score-table"
import { LeverageTrendChart } from "@/components/maturity/leverage-trend-chart"
import { ProjectReadinessTable } from "@/components/maturity/project-readiness-table"
import { CardSkeleton, ChartSkeleton, TableSkeleton } from "@/components/shared/loading-skeleton"
import type { DateRange } from "@/components/layout/date-range-picker"

const tabs = [
  { id: "overview", label: "Overview" },
  { id: "agents", label: "Agents & Skills" },
  { id: "engineers", label: "Engineers" },
  { id: "projects", label: "Projects" },
] as const

type TabId = (typeof tabs)[number]["id"]

interface MaturityPageProps {
  teamId: string | null
  dateRange: DateRange | null
}

export function MaturityPage({ teamId, dateRange }: MaturityPageProps) {
  const [activeTab, setActiveTab] = useState<TabId>("overview")
  const startDate = dateRange?.startDate
  const endDate = dateRange?.endDate
  const { data, isLoading } = useMaturityAnalytics(teamId, startDate, endDate)

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">AI Maturity</h1>

      <PageTabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      {isLoading && (
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-3">
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
          </div>
          <ChartSkeleton />
          <TableSkeleton />
        </div>
      )}

      {data && activeTab === "overview" && (
        <div className="space-y-6">
          <MaturitySummary data={data} />
          <ToolCategoryChart data={data.tool_categories} />
        </div>
      )}

      {data && activeTab === "agents" && (
        <AgentSkillTable data={data.agent_skill_breakdown} />
      )}

      {data && activeTab === "engineers" && (
        <div className="space-y-6">
          <LeverageScoreTable data={data.engineer_profiles} />
          <LeverageTrendChart data={data.daily_leverage} />
        </div>
      )}

      {data && activeTab === "projects" && (
        <ProjectReadinessTable data={data.project_readiness} />
      )}
    </div>
  )
}
