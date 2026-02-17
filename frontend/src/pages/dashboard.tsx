import { useSearchParams } from "react-router-dom"
import { useOverview, useTeam } from "@/hooks/use-api-queries"
import { InlineStat } from "@/components/ui/inline-stat"
import { PageTabs } from "@/components/ui/page-tabs"
import { Button } from "@/components/ui/button"
import { OverviewTab } from "@/components/dashboard-v2/overview-tab"
import { EngineersTab } from "@/components/dashboard-v2/engineers-tab"
import { ProjectsTab } from "@/components/dashboard-v2/projects-tab"
import { SessionsTab } from "@/components/dashboard-v2/sessions-tab"
import { QualityTab } from "@/components/dashboard-v2/quality-tab"
import { InsightsTab } from "@/components/dashboard-v2/insights-tab"
import { CardSkeleton } from "@/components/shared/loading-skeleton"
import { formatNumber, formatCost, formatPercent, formatDuration } from "@/lib/utils"
import { exportToCsv } from "@/lib/csv-export"
import { exportToPdf } from "@/lib/pdf-export"
import { Download, FileText } from "lucide-react"
import type { DateRange } from "@/components/layout/date-range-picker"

const tabs = [
  { id: "overview", label: "Overview" },
  { id: "engineers", label: "Engineers" },
  { id: "projects", label: "Projects" },
  { id: "sessions", label: "Sessions" },
  { id: "quality", label: "Quality" },
  { id: "insights", label: "Insights" },
] as const

type TabId = (typeof tabs)[number]["id"]

interface DashboardPageProps {
  teamId: string | null
  dateRange: DateRange | null
}

export function DashboardPage({ teamId, dateRange }: DashboardPageProps) {
  const [searchParams, setSearchParams] = useSearchParams()
  const activeTab = (searchParams.get("tab") as TabId) || "overview"
  const startDate = dateRange?.startDate
  const endDate = dateRange?.endDate

  const { data: overview, isLoading: loadingOverview } = useOverview(teamId, startDate, endDate)
  const { data: team } = useTeam(teamId ?? "")

  const handleTabChange = (tab: TabId) => {
    setSearchParams(tab === "overview" ? {} : { tab })
  }

  const handleExportCsv = () => {
    if (!overview) return
    const headers = ["Metric", "Value"]
    const rows = [
      ["Sessions", overview.total_sessions],
      ["Engineers", overview.total_engineers],
      ["Cost", overview.estimated_cost ?? 0],
      ["Success Rate", overview.success_rate != null ? `${(overview.success_rate * 100).toFixed(1)}%` : "-"],
      ["Avg Duration", overview.avg_session_duration ?? 0],
    ]
    exportToCsv("dashboard-summary.csv", headers, rows)
  }

  const handleExportPdf = () => {
    if (!overview) return
    const headers = ["Metric", "Value"]
    const rows = [
      ["Sessions", overview.total_sessions],
      ["Engineers", overview.total_engineers],
      ["Cost", overview.estimated_cost != null ? formatCost(overview.estimated_cost) : "-"],
      ["Success Rate", formatPercent(overview.success_rate)],
      ["Avg Duration", formatDuration(overview.avg_session_duration)],
    ]
    exportToPdf("dashboard-summary.pdf", "Dashboard Summary", headers, rows)
  }

  if (loadingOverview) {
    return (
      <div className="space-y-6">
        <CardSkeleton />
        <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      </div>
    )
  }

  if (!overview) return null

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{team?.name ?? "Organization"}</h1>
          <p className="text-sm text-muted-foreground">
            {formatNumber(overview.total_engineers)} engineers
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleExportCsv}>
            <Download className="mr-1 h-4 w-4" />
            CSV
          </Button>
          <Button variant="outline" size="sm" onClick={handleExportPdf}>
            <FileText className="mr-1 h-4 w-4" />
            PDF
          </Button>
        </div>
      </div>

      {/* KPI row */}
      <div className="flex gap-8 border-b border-border pb-4">
        <InlineStat label="Sessions" value={formatNumber(overview.total_sessions)} />
        <InlineStat label="Engineers" value={formatNumber(overview.total_engineers)} />
        <InlineStat
          label="Cost"
          value={overview.estimated_cost != null ? formatCost(overview.estimated_cost) : "-"}
        />
        <InlineStat label="Success Rate" value={formatPercent(overview.success_rate)} />
        <InlineStat label="Avg Duration" value={formatDuration(overview.avg_session_duration)} />
        <InlineStat
          label="Health Score"
          value={overview.avg_health_score != null ? overview.avg_health_score.toFixed(1) : "-"}
        />
      </div>

      {/* Tabs */}
      <PageTabs tabs={tabs} activeTab={activeTab} onChange={handleTabChange} />

      {/* Tab content */}
      <div>
        {activeTab === "overview" && (
          <OverviewTab overview={overview} teamId={teamId} startDate={startDate} endDate={endDate} />
        )}
        {activeTab === "engineers" && (
          <EngineersTab teamId={teamId} startDate={startDate} endDate={endDate} />
        )}
        {activeTab === "projects" && (
          <ProjectsTab teamId={teamId} startDate={startDate} endDate={endDate} />
        )}
        {activeTab === "sessions" && (
          <SessionsTab teamId={teamId} dateRange={dateRange} />
        )}
        {activeTab === "quality" && (
          <QualityTab teamId={teamId} startDate={startDate} endDate={endDate} />
        )}
        {activeTab === "insights" && (
          <InsightsTab teamId={teamId} startDate={startDate} endDate={endDate} />
        )}
      </div>
    </div>
  )
}
