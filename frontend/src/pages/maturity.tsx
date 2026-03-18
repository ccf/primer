import { useState } from "react"
import { TrendingUp } from "lucide-react"
import { useMaturityAnalytics, useToolAdoption } from "@/hooks/use-api-queries"
import { PageTabs } from "@/components/ui/page-tabs"
import { PageHeader } from "@/components/shared/page-header"
import { MaturitySummary } from "@/components/maturity/maturity-summary"
import { ToolCategoryChart } from "@/components/maturity/tool-category-chart"
import { AgentSkillTable } from "@/components/maturity/agent-skill-table"
import { CustomizationBreakdownTable } from "@/components/maturity/customization-breakdown-table"
import { LeverageScoreTable } from "@/components/maturity/leverage-score-table"
import { LeverageTrendChart } from "@/components/maturity/leverage-trend-chart"
import { EffectivenessScatter } from "@/components/maturity/effectiveness-scatter"
import { ProjectReadinessTable } from "@/components/maturity/project-readiness-table"
import { ToolAdoptionSummary } from "@/components/tools/tool-adoption-summary"
import { ToolAdoptionChart } from "@/components/tools/tool-adoption-chart"
import { ToolTrendChart } from "@/components/tools/tool-trend-chart"
import { EngineerToolTable } from "@/components/tools/engineer-tool-table"
import { CardSkeleton, ChartSkeleton, TableSkeleton } from "@/components/shared/loading-skeleton"
import type { DateRange } from "@/components/layout/date-range-picker"

const tabs = [
  { id: "overview", label: "Overview" },
  { id: "agents", label: "Agents & Skills" },
  { id: "tools", label: "Tools" },
  { id: "engineers", label: "Engineers" },
  { id: "effectiveness", label: "Effectiveness" },
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
  const { data: toolData, isLoading: loadingTools } = useToolAdoption(teamId, startDate, endDate)

  return (
    <div className="space-y-6">
      <PageHeader
        icon={TrendingUp}
        title="AI Maturity"
        description="Adoption, leverage, and tool proficiency"
      />

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
        <div className="space-y-6">
          <AgentSkillTable data={data.agent_skill_breakdown} />
          <CustomizationBreakdownTable data={data.customization_breakdown} />
        </div>
      )}

      {activeTab === "tools" && loadingTools && (
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-3">
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
          </div>
          <ChartSkeleton />
        </div>
      )}

      {activeTab === "tools" && toolData && (
        <div className="space-y-6">
          <ToolAdoptionSummary data={toolData} />
          <div className="grid gap-6 lg:grid-cols-2">
            <ToolAdoptionChart data={toolData.tool_adoption} />
            <ToolTrendChart data={toolData.tool_trends} />
          </div>
          <EngineerToolTable data={toolData.engineer_profiles} />
        </div>
      )}

      {data && activeTab === "engineers" && (
        <div className="space-y-6">
          <LeverageScoreTable data={data.engineer_profiles} />
          <LeverageTrendChart data={data.daily_leverage} />
        </div>
      )}

      {data && activeTab === "effectiveness" && (
        <EffectivenessScatter data={data.engineer_profiles} />
      )}

      {data && activeTab === "projects" && (
        <ProjectReadinessTable data={data.project_readiness} />
      )}
    </div>
  )
}
