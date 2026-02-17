import { useQualityMetrics } from "@/hooks/use-api-queries"
import { QualityOverviewCards } from "@/components/quality/quality-overview"
import { CodeVolumeChart } from "@/components/quality/code-volume-chart"
import { PRTable } from "@/components/quality/pr-table"
import { ClaudePRComparison } from "@/components/quality/claude-pr-comparison"
import { GitHubStatusBanner } from "@/components/quality/github-status-banner"
import { CardSkeleton } from "@/components/shared/loading-skeleton"

interface QualityTabProps {
  teamId: string | null
  startDate?: string
  endDate?: string
}

export function QualityTab({ teamId, startDate, endDate }: QualityTabProps) {
  const { data, isLoading } = useQualityMetrics(teamId, startDate, endDate)

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
        <CardSkeleton />
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="space-y-6">
      <GitHubStatusBanner connected={data.github_connected} />
      <QualityOverviewCards overview={data.overview} />
      {data.daily_volume.length > 0 && <CodeVolumeChart data={data.daily_volume} />}
      {data.recent_prs.length > 0 && <PRTable prs={data.recent_prs} />}
      <ClaudePRComparison teamId={teamId} startDate={startDate} endDate={endDate} />
    </div>
  )
}
