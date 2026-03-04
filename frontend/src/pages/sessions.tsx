import { useState } from "react"
import { MonitorDot } from "lucide-react"
import { useAuth } from "@/lib/auth-context"
import { useFriction } from "@/hooks/use-api-queries"
import { SessionBrowser } from "@/components/sessions/session-browser"
import { FrictionList } from "@/components/analytics/friction-list"
import { InsightsTab } from "@/components/session-insights/insights-tab"
import { PageHeader } from "@/components/shared/page-header"
import { PageTabs } from "@/components/ui/page-tabs"
import { ChartSkeleton } from "@/components/shared/loading-skeleton"
import type { DateRange } from "@/components/layout/date-range-picker"

const tabs = [
  { id: "browse", label: "Browse" },
  { id: "insights", label: "Insights" },
] as const

type TabId = (typeof tabs)[number]["id"]

interface SessionsPageProps {
  teamId: string | null
  dateRange: DateRange | null
}

export function SessionsPage({ teamId, dateRange }: SessionsPageProps) {
  const [activeTab, setActiveTab] = useState<TabId>("browse")
  const { user } = useAuth()
  const role = user?.role ?? "admin"
  const startDate = dateRange?.startDate
  const endDate = dateRange?.endDate
  const { data: friction, isLoading: loadingFriction } = useFriction(teamId, startDate, endDate)

  return (
    <div className="space-y-6">
      <PageHeader
        icon={MonitorDot}
        title={role === "engineer" ? "My Sessions" : "Sessions"}
        description="Browse sessions and analyze aggregate patterns"
      />

      <PageTabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      {activeTab === "browse" && (
        <>
          <SessionBrowser
            teamId={teamId}
            dateRange={dateRange}
            showEngineerFilter={role === "admin"}
          />
          {loadingFriction ? <ChartSkeleton /> : friction && <FrictionList data={friction} />}
        </>
      )}

      {activeTab === "insights" && (
        <InsightsTab teamId={teamId} startDate={startDate} endDate={endDate} />
      )}
    </div>
  )
}
