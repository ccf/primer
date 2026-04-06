import { useState } from "react"
import { useQualityMetrics, useReviewFindings } from "@/hooks/use-api-queries"
import { PageHeader } from "@/components/shared/page-header"
import { PageTabs } from "@/components/ui/page-tabs"
import { QualityOverviewCards } from "@/components/quality/quality-overview"
import { ClaudePRComparison } from "@/components/quality/claude-pr-comparison"
import { PRTable } from "@/components/quality/pr-table"
import { CodeVolumeChart } from "@/components/quality/code-volume-chart"
import { QualityByTypeChart } from "@/components/quality/quality-by-type"
import { GitHubStatusBanner } from "@/components/quality/github-status-banner"
import { EngineerQualityTable } from "@/components/quality/engineer-quality-table"
import { FindingsOverviewSection } from "@/components/quality/findings-overview"
import { FindingsTable } from "@/components/quality/findings-table"
import { PostMergeOutcomesSection } from "@/components/quality/post-merge-outcomes-section"
import { QualityAttributionTable } from "@/components/quality/quality-attribution-table"
import { CardSkeleton, ChartSkeleton } from "@/components/shared/loading-skeleton"
import { SectionHeader } from "@/components/shared/section-header"
import { GitPullRequest } from "lucide-react"
import type { DateRange } from "@/components/layout/date-range-picker"

const tabs = [
  { id: "overview", label: "Overview" },
  { id: "findings", label: "Findings" },
  { id: "outcomes", label: "Outcomes" },
] as const

type TabId = (typeof tabs)[number]["id"]

interface QualityPageProps {
  teamId: string | null
  dateRange: DateRange | null
}

export function QualityPage({ teamId, dateRange }: QualityPageProps) {
  const startDate = dateRange?.startDate
  const endDate = dateRange?.endDate
  const [activeTab, setActiveTab] = useState<TabId>("overview")

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
        description="PR metrics, review findings, and post-merge outcomes"
      />

      <GitHubStatusBanner connected={quality.github_connected} />

      <PageTabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      <div className="mt-6">
        {activeTab === "overview" && (
          <div className="space-y-8">
            <QualityOverviewCards overview={quality.overview} />

            <div className="grid gap-6 lg:grid-cols-2">
              <ClaudePRComparison teamId={teamId} startDate={startDate} endDate={endDate} />
              <QualityByTypeChart data={quality.by_session_type} />
            </div>

            <section className="space-y-3">
              <SectionHeader
                title="Recent pull requests"
                description="PRs and review behavior feeding the quality view."
              />
              <PRTable prs={quality.recent_prs} />
            </section>

            <section className="space-y-3">
              <SectionHeader
                title="Engineer quality"
                description="Who is generating strong outcomes and where quality support is needed."
              />
              <EngineerQualityTable engineers={quality.engineer_quality} />
            </section>
          </div>
        )}

        {activeTab === "findings" && (
          <div className="space-y-8">
            {quality.findings_overview && (
              <FindingsOverviewSection findings={quality.findings_overview} />
            )}

            {findingsData && findingsData.items.length > 0 && (
              <section className="space-y-3">
                <SectionHeader
                  title="Review findings detail"
                  description="Automated review issues behind the summary metrics."
                />
                <FindingsTable findings={findingsData.items} />
              </section>
            )}

            <section className="space-y-3">
              <QualityAttributionTable rows={quality.attribution} />
            </section>
          </div>
        )}

        {activeTab === "outcomes" && (
          <div className="space-y-8">
            <section className="space-y-3">
              <SectionHeader
                title="Post-merge outcomes"
                description="Stabilization work after merge: reverts, hotfixes, and follow-up fixes."
              />
              <PostMergeOutcomesSection
                summary={quality.post_merge_outcomes}
                prs={quality.recent_post_merge_prs}
              />
            </section>

            <CodeVolumeChart data={quality.daily_volume} />
          </div>
        )}
      </div>
    </div>
  )
}
