import { useToolAdoption } from "@/hooks/use-api-queries"
import { ToolAdoptionSummary } from "@/components/tools/tool-adoption-summary"
import { ToolAdoptionChart } from "@/components/tools/tool-adoption-chart"
import { ToolTrendChart } from "@/components/tools/tool-trend-chart"
import { EngineerToolTable } from "@/components/tools/engineer-tool-table"
import { CardSkeleton, ChartSkeleton } from "@/components/shared/loading-skeleton"
import { EmptyState } from "@/components/shared/empty-state"
import type { DateRange } from "@/components/layout/date-range-picker"

interface ToolAdoptionPageProps {
  teamId: string | null
  dateRange: DateRange | null
}

export function ToolAdoptionPage({ teamId, dateRange }: ToolAdoptionPageProps) {
  const startDate = dateRange?.startDate
  const endDate = dateRange?.endDate
  const { data, isLoading } = useToolAdoption(teamId, startDate, endDate)

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Tool Adoption</h1>
        <div className="grid gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
        <ChartSkeleton />
      </div>
    )
  }

  if (!data || data.total_engineers === 0) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Tool Adoption</h1>
        <EmptyState message="No tool usage data available" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Tool Adoption</h1>
      <ToolAdoptionSummary data={data} />
      <ToolAdoptionChart data={data.tool_adoption} />
      <ToolTrendChart data={data.tool_trends} />
      <EngineerToolTable data={data.engineer_profiles} />
    </div>
  )
}
