import { useState } from "react"
import { useProjectAnalytics } from "@/hooks/use-api-queries"
import { ProjectTable } from "@/components/projects/project-table"
import { TableSkeleton } from "@/components/shared/loading-skeleton"
import { EmptyState } from "@/components/shared/empty-state"

interface ProjectsTabProps {
  teamId: string | null
  startDate?: string
  endDate?: string
}

export function ProjectsTab({ teamId, startDate, endDate }: ProjectsTabProps) {
  const [sortBy, setSortBy] = useState("total_sessions")
  const { data, isLoading } = useProjectAnalytics(teamId, startDate, endDate, sortBy)

  if (isLoading) return <TableSkeleton />

  if (!data || data.projects.length === 0) {
    return <EmptyState message="No projects found" />
  }

  return <ProjectTable projects={data.projects} onSortChange={setSortBy} sortBy={sortBy} />
}
