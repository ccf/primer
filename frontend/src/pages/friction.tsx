import { useState } from "react"
import { useBottleneckAnalytics } from "@/hooks/use-api-queries"
import { formatNumber, formatPercent } from "@/lib/utils"
import { PageHeader } from "@/components/shared/page-header"
import { PageTabs } from "@/components/ui/page-tabs"
import { BottleneckSummary } from "@/components/bottlenecks/bottleneck-summary"
import { FrictionTrendChart } from "@/components/bottlenecks/friction-trend-chart"
import { FrictionImpactTable } from "@/components/bottlenecks/friction-impact-table"
import { ProjectFrictionTable } from "@/components/bottlenecks/project-friction-table"
import { EngineerTimeLostTable } from "@/components/bottlenecks/engineer-time-lost-table"
import { RootCauseClusterList } from "@/components/bottlenecks/root-cause-cluster-list"
import { RecoveryPatternList } from "@/components/bottlenecks/recovery-pattern-list"
import { CardSkeleton, ChartSkeleton } from "@/components/shared/loading-skeleton"
import { AlertTriangle } from "lucide-react"
import type { DateRange } from "@/components/layout/date-range-picker"

const tabs = [
  { id: "overview", label: "Overview" },
  { id: "root-causes", label: "Root Causes" },
  { id: "by-project", label: "By Project" },
  { id: "by-engineer", label: "By Engineer" },
] as const

type TabId = (typeof tabs)[number]["id"]

interface FrictionPageProps {
  teamId: string | null
  dateRange: DateRange | null
}

export function FrictionPage({ teamId, dateRange }: FrictionPageProps) {
  const startDate = dateRange?.startDate
  const endDate = dateRange?.endDate
  const { data, isLoading } = useBottleneckAnalytics(teamId, startDate, endDate)
  const [activeTab, setActiveTab] = useState<TabId>("overview")

  if (isLoading) {
    return (
      <div className="space-y-6">
        <CardSkeleton />
        <div className="grid gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
        <ChartSkeleton />
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="space-y-8">
      <PageHeader
        icon={AlertTriangle}
        title="Friction Intelligence"
        description={
          data.overall_friction_rate != null
            ? `${formatPercent(data.overall_friction_rate)} of sessions hit friction across ${formatNumber(data.sessions_with_any_friction)} sessions`
            : "What's blocking your engineers and how much it costs"
        }
      />

      <BottleneckSummary data={data} />

      <PageTabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      <div className="mt-6">
        {activeTab === "overview" && (
          <div className="space-y-8">
            <div className="grid gap-6 lg:grid-cols-2">
              <FrictionTrendChart data={data.friction_trends} />
              <FrictionImpactTable data={data.friction_impacts} />
            </div>
          </div>
        )}

        {activeTab === "root-causes" && (
          <div className="space-y-8">
            <RootCauseClusterList data={data.root_cause_clusters} />

            <RecoveryPatternList
              overview={data.recovery_overview}
              patterns={data.recovery_patterns}
            />
          </div>
        )}

        {activeTab === "by-project" && (
          <div className="space-y-3">
            <div>
              <h2 className="text-sm font-semibold text-muted-foreground">Friction by Project</h2>
              <p className="text-xs text-muted-foreground/80">
                Which repositories generate the most friction and where enablement work would help.
              </p>
            </div>
            <ProjectFrictionTable data={data.project_friction} />
          </div>
        )}

        {activeTab === "by-engineer" && (
          <div className="space-y-3">
            <div>
              <h2 className="text-sm font-semibold text-muted-foreground">Time Lost by Engineer</h2>
              <p className="text-xs text-muted-foreground/80">
                Estimated engineering minutes lost to friction, broken down by engineer and friction type.
              </p>
            </div>
            <EngineerTimeLostTable data={data.engineer_time_lost} />
          </div>
        )}
      </div>
    </div>
  )
}
