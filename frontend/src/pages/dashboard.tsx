import { useSearchParams } from "react-router-dom"
import { useOverview, useTeam } from "@/hooks/use-api-queries"
import { InlineStat } from "@/components/ui/inline-stat"
import { PageTabs } from "@/components/ui/page-tabs"
import { Button } from "@/components/ui/button"
import { PageHeader } from "@/components/shared/page-header"
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
import {
  Download,
  FileText,
  LayoutDashboard,
  Activity,
  Users,
  DollarSign,
  Target,
  Clock,
  Heart,
} from "lucide-react"
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

const validTabIds = new Set<string>(tabs.map((t) => t.id))

interface DashboardPageProps {
  teamId: string | null
  dateRange: DateRange | null
}

export function DashboardPage({ teamId, dateRange }: DashboardPageProps) {
  const [searchParams, setSearchParams] = useSearchParams()
  const rawTab = searchParams.get("tab")
  const activeTab: TabId = rawTab && validTabIds.has(rawTab) ? (rawTab as TabId) : "overview"
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

  const kpiItems = [
    { label: "Sessions", value: formatNumber(overview.total_sessions), icon: Activity },
    { label: "Engineers", value: formatNumber(overview.total_engineers), icon: Users },
    { label: "Cost", value: overview.estimated_cost != null ? formatCost(overview.estimated_cost) : "-", icon: DollarSign },
    { label: "Success Rate", value: formatPercent(overview.success_rate), icon: Target },
    { label: "Avg Duration", value: formatDuration(overview.avg_session_duration), icon: Clock },
    { label: "Health Score", value: overview.avg_health_score != null ? overview.avg_health_score.toFixed(1) : "-", icon: Heart },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        icon={LayoutDashboard}
        title={team?.name ?? "Organization"}
        description={`${formatNumber(overview.total_engineers)} engineers`}
      >
        <Button variant="outline" size="sm" onClick={handleExportCsv}>
          <Download className="mr-1 h-4 w-4" />
          CSV
        </Button>
        <Button variant="outline" size="sm" onClick={handleExportPdf}>
          <FileText className="mr-1 h-4 w-4" />
          PDF
        </Button>
      </PageHeader>

      {/* KPI row */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {kpiItems.map((item, i) => (
          <div
            key={item.label}
            className="animate-stagger-in"
            style={{ animationDelay: `${i * 50}ms` }}
          >
            <InlineStat label={item.label} value={item.value} icon={item.icon} />
          </div>
        ))}
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
