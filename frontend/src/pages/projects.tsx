import { useState } from "react"
import { FolderKanban, Coins, FolderGit2, Sparkles } from "lucide-react"
import { useProjectAnalytics, useProjectComparison } from "@/hooks/use-api-queries"
import { PageHeader } from "@/components/shared/page-header"
import { CardSkeleton } from "@/components/shared/loading-skeleton"
import { ProjectComparisonCard } from "@/components/projects/project-comparison-card"
import { InlineStat } from "@/components/ui/inline-stat"
import { ProjectTable } from "@/components/projects/project-table"
import { formatCost, formatNumber, formatTokens } from "@/lib/utils"
import type { DateRange } from "@/components/layout/date-range-picker"

interface ProjectsPageProps {
  teamId: string | null
  dateRange: DateRange | null
}

export function ProjectsPage({ teamId, dateRange }: ProjectsPageProps) {
  const [sortBy, setSortBy] = useState("total_sessions")
  const startDate = dateRange?.startDate
  const endDate = dateRange?.endDate
  const { data, isLoading } = useProjectAnalytics(teamId, startDate, endDate, sortBy)
  const { data: comparison } = useProjectComparison(teamId, startDate, endDate)

  if (isLoading) {
    return (
      <div className="space-y-6">
        <CardSkeleton />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <CardSkeleton key={index} />
          ))}
        </div>
        <CardSkeleton />
      </div>
    )
  }

  if (!data) return null

  const totalSessions = data.projects.reduce((sum, project) => sum + project.total_sessions, 0)
  const totalTokens = data.projects.reduce((sum, project) => sum + project.total_tokens, 0)
  const totalCost = data.projects.reduce((sum, project) => sum + project.estimated_cost, 0)

  return (
    <div className="space-y-8">
      <PageHeader
        icon={FolderKanban}
        title="Projects"
        description="Dedicated workspaces for readiness, friction, quality, cost, and enablement"
      />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <InlineStat label="Active Projects" value={formatNumber(data.total_count)} icon={FolderGit2} />
        <InlineStat label="Sessions" value={formatNumber(totalSessions)} icon={Sparkles} />
        <InlineStat label="Tracked Tokens" value={formatTokens(totalTokens)} icon={FolderKanban} />
        <InlineStat label="Estimated Spend" value={formatCost(totalCost)} icon={Coins} />
      </div>

      {comparison ? <ProjectComparisonCard comparison={comparison} /> : null}

      <ProjectTable projects={data.projects} onSortChange={setSortBy} sortBy={sortBy} />
    </div>
  )
}
