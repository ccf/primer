import {
  useDailyStats,
  useOverview,
  useRecommendations,
  useActivityHeatmap,
  useTeam,
} from "@/hooks/use-api-queries"
import { InlineStat } from "@/components/ui/inline-stat"
import { Button } from "@/components/ui/button"
import { PageHeader } from "@/components/shared/page-header"
import { DailyActivityChart } from "@/components/dashboard/daily-activity-chart"
import { ActivityHeatmap } from "@/components/dashboard/activity-heatmap"
import { OutcomeChart } from "@/components/dashboard/outcome-chart"
import { RecommendationsPanel } from "@/components/dashboard/recommendations-panel"
import { AttentionSection } from "@/components/dashboard/attention-section"
import { DeepDiveCards } from "@/components/dashboard/deep-dive-cards"
import { CardSkeleton, ChartSkeleton } from "@/components/shared/loading-skeleton"
import { formatNumber, formatPercent, formatDuration } from "@/lib/utils"
import { exportToCsv } from "@/lib/csv-export"
import { exportToPdf } from "@/lib/pdf-export"
import {
  Download,
  FileText,
  LayoutDashboard,
  Activity,
  Users,
  Target,
  Clock,
  Heart,
} from "lucide-react"
import type { DateRange } from "@/components/layout/date-range-picker"

interface DashboardPageProps {
  teamId: string | null
  dateRange: DateRange | null
}

export function DashboardPage({ teamId, dateRange }: DashboardPageProps) {
  const startDate = dateRange?.startDate
  const endDate = dateRange?.endDate

  const { data: overview, isLoading: loadingOverview } = useOverview(teamId, startDate, endDate)
  const { data: team } = useTeam(teamId ?? "")
  const { data: daily, isLoading: loadingDaily } = useDailyStats(teamId, 30, startDate, endDate)
  const { data: heatmap, isLoading: loadingHeatmap } = useActivityHeatmap(teamId, startDate, endDate)
  const { data: recs, isLoading: loadingRecs } = useRecommendations(teamId, startDate, endDate)

  const handleExportCsv = () => {
    if (!overview) return
    const headers = ["Metric", "Value"]
    const rows = [
      ["Sessions", overview.total_sessions],
      ["Engineers", overview.total_engineers],
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
      ["Success Rate", formatPercent(overview.success_rate)],
      ["Avg Duration", formatDuration(overview.avg_session_duration)],
    ]
    exportToPdf("dashboard-summary.pdf", "Dashboard Summary", headers, rows)
  }

  if (loadingOverview) {
    return (
      <div className="space-y-6">
        <CardSkeleton />
        <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
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
    { label: "Success Rate", value: formatPercent(overview.success_rate), icon: Target },
    { label: "Avg Duration", value: formatDuration(overview.avg_session_duration), icon: Clock },
    {
      label: "Health Score",
      value: overview.avg_health_score != null ? overview.avg_health_score.toFixed(1) : "-",
      icon: Heart,
    },
  ]

  return (
    <div className="space-y-8">
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

      {/* KPI Strip */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
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

      {/* Activity Section */}
      <section className="space-y-4">
        <h2 className="text-sm font-semibold text-muted-foreground">Activity</h2>
        <div className="grid gap-4 lg:grid-cols-2">
          {loadingDaily ? <ChartSkeleton /> : daily && <DailyActivityChart data={daily} />}
          <OutcomeChart data={overview.outcome_counts} />
        </div>
        {loadingHeatmap
          ? <ChartSkeleton />
          : heatmap && heatmap.cells.length > 0 && <ActivityHeatmap data={heatmap} />}
      </section>

      {/* Attention Section */}
      <section>
        <AttentionSection />
      </section>

      {/* Deep-Dive Cards */}
      <section>
        <DeepDiveCards teamId={teamId} startDate={startDate} endDate={endDate} />
      </section>

      {/* Recommendations */}
      <section>
        {loadingRecs ? <ChartSkeleton /> : recs && <RecommendationsPanel data={recs} />}
      </section>
    </div>
  )
}
