import { useState } from "react"
import { useProjectAnalytics } from "@/hooks/use-api-queries"
import { ProjectTable } from "@/components/projects/project-table"
import { TableSkeleton } from "@/components/shared/loading-skeleton"
import { EmptyState } from "@/components/shared/empty-state"
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

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Projects</h1>
        <TableSkeleton />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Projects</h1>
      {!data || data.projects.length === 0 ? (
        <EmptyState message="No projects found" />
      ) : (
        <ProjectTable
          projects={data.projects}
          onSortChange={setSortBy}
          sortBy={sortBy}
        />
      )}
    </div>
  )
}
