import { useState } from "react"
import { Download } from "lucide-react"
import { useProjectAnalytics } from "@/hooks/use-api-queries"
import { ProjectTable } from "@/components/projects/project-table"
import { TableSkeleton } from "@/components/shared/loading-skeleton"
import { EmptyState } from "@/components/shared/empty-state"
import { Button } from "@/components/ui/button"
import { exportToCsv } from "@/lib/csv-export"
import { formatCost } from "@/lib/utils"
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

  const handleExport = () => {
    if (!data) return
    exportToCsv(
      "projects.csv",
      ["Project", "Sessions", "Engineers", "Tokens", "Estimated Cost"],
      data.projects.map((p) => [
        p.project_name,
        p.total_sessions,
        p.unique_engineers,
        p.total_tokens,
        formatCost(p.estimated_cost),
      ]),
    )
  }

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
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Projects</h1>
        {data && data.projects.length > 0 && (
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download className="mr-1 h-4 w-4" />
            Export CSV
          </Button>
        )}
      </div>
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
