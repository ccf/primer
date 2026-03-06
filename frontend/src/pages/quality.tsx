import { useQualityMetrics, useReviewFindings } from "@/hooks/use-api-queries"
import { PageHeader } from "@/components/shared/page-header"
import { QualityOverviewCards } from "@/components/quality/quality-overview"
import { ClaudePRComparison } from "@/components/quality/claude-pr-comparison"
import { PRTable } from "@/components/quality/pr-table"
import { CodeVolumeChart } from "@/components/quality/code-volume-chart"
import { QualityByTypeChart } from "@/components/quality/quality-by-type"
import { GitHubStatusBanner } from "@/components/quality/github-status-banner"
import { EngineerQualityTable } from "@/components/quality/engineer-quality-table"
import { FindingsOverviewSection } from "@/components/quality/findings-overview"
import { FindingsTable } from "@/components/quality/findings-table"
import { CardSkeleton, ChartSkeleton } from "@/components/shared/loading-skeleton"
import { GitPullRequest } from "lucide-react"
import type { DateRange } from "@/components/layout/date-range-picker"

interface QualityPageProps {
  teamId: string | null
  dateRange: DateRange | null
}

export function QualityPage({ teamId, dateRange }: QualityPageProps) {
  const startDate = dateRange?.startDate
  const endDate = dateRange?.endDate

  const { data: quality, isLoading } = useQualityMetrics(teamId, startDate, endDate)
  const { data: findingsData } = useReviewFindings(teamId, startDate, endDate)

  if (isLoading) {
    return (
      <div className="space-y-6">
        <CardSkeleton />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
        <ChartSkeleton />
      </div>
    )
  }

  if (!quality) return null

  return (
    <div className="space-y-8">
      <PageHeader
        icon={GitPullRequest}
        title="Code Quality"
        description="PR metrics, code volume, and Claude-assisted comparison"
      />

      <GitHubStatusBanner connected={quality.github_connected} />

      <QualityOverviewCards overview={quality.overview} />

      <div className="grid gap-6 lg:grid-cols-2">
        <ClaudePRComparison teamId={teamId} startDate={startDate} endDate={endDate} />
        <QualityByTypeChart data={quality.by_session_type} />
      </div>

      {quality.findings_overview && (
        <FindingsOverviewSection findings={quality.findings_overview} />
      )}

      {findingsData && findingsData.items.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-sm font-semibold text-muted-foreground">
            Review Findings Detail
          </h2>
          <FindingsTable findings={findingsData.items} />
        </section>
      )}

      <CodeVolumeChart data={quality.daily_volume} />

      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-muted-foreground">Pull Requests</h2>
        <PRTable prs={quality.recent_prs} />
      </section>

      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-muted-foreground">Engineer Quality</h2>
        <EngineerQualityTable engineers={quality.engineer_quality} />
      </section>
    </div>
  )
}
