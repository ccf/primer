import { useState } from "react"
import { cn } from "@/lib/utils"
import { useQualityMetrics } from "@/hooks/use-api-queries"
import { QualityOverviewCards } from "@/components/quality/quality-overview"
import { CodeVolumeChart } from "@/components/quality/code-volume-chart"
import { QualityByTypeChart } from "@/components/quality/quality-by-type"
import { PRTable } from "@/components/quality/pr-table"
import { EngineerQualityTable } from "@/components/quality/engineer-quality-table"
import { GitHubStatusBanner } from "@/components/quality/github-status-banner"
import { CardSkeleton } from "@/components/shared/loading-skeleton"
import type { DateRange } from "@/components/layout/date-range-picker"

const tabs = [
  { id: "code", label: "Code Output" },
  { id: "prs", label: "Pull Requests" },
  { id: "engineers", label: "Engineers" },
] as const

type TabId = (typeof tabs)[number]["id"]

interface QualityPageProps {
  teamId: string | null
  dateRange: DateRange | null
}

export function QualityPage({ teamId, dateRange }: QualityPageProps) {
  const [activeTab, setActiveTab] = useState<TabId>("code")
  const startDate = dateRange?.startDate
  const endDate = dateRange?.endDate
  const { data, isLoading } = useQualityMetrics(teamId, startDate, endDate)

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Quality</h1>

      <div className="flex gap-1 border-b border-border">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "px-4 py-2 text-sm font-medium transition-colors",
              activeTab === tab.id
                ? "border-b-2 border-primary text-primary"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {isLoading && (
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-5">
            {Array.from({ length: 5 }).map((_, i) => (
              <CardSkeleton key={i} />
            ))}
          </div>
          <CardSkeleton />
        </div>
      )}

      {!isLoading && data && (
        <>
          <GitHubStatusBanner connected={data.github_connected} />
          <QualityOverviewCards overview={data.overview} />

          {activeTab === "code" && (
            <div className="space-y-6">
              <CodeVolumeChart data={data.daily_volume} />
              <QualityByTypeChart data={data.by_session_type} />
            </div>
          )}

          {activeTab === "prs" && <PRTable prs={data.recent_prs} />}

          {activeTab === "engineers" && (
            <EngineerQualityTable engineers={data.engineer_quality} />
          )}

          {data.sessions_analyzed === 0 && (
            <div className="py-8 text-center text-sm text-muted-foreground">
              No session data with commits available for quality analysis.
            </div>
          )}
        </>
      )}
    </div>
  )
}
