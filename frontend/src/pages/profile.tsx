import { useSearchParams } from "react-router-dom"
import { useAuth } from "@/lib/auth-context"
import { useEngineerProfile } from "@/hooks/use-api-queries"
import { PageTabs } from "@/components/ui/page-tabs"
import { ProfileSidebar } from "@/components/shared/profile-sidebar"
import { ProfileOverviewTab } from "@/components/profile/profile-overview-tab"
import { ProfileSessionsTab } from "@/components/profile/profile-sessions-tab"
import { ProfileInsightsTab } from "@/components/profile/profile-insights-tab"
import { ProfileGrowthTab } from "@/components/profile/profile-growth-tab"
import { CardSkeleton } from "@/components/shared/loading-skeleton"
import type { DateRange } from "@/components/layout/date-range-picker"

const tabs = [
  { id: "overview", label: "Overview" },
  { id: "sessions", label: "Sessions" },
  { id: "insights", label: "Insights" },
  { id: "growth", label: "Growth" },
] as const

type TabId = (typeof tabs)[number]["id"]

const validTabIds = new Set<string>(tabs.map((t) => t.id))

interface ProfilePageProps {
  teamId: string | null
  dateRange: DateRange | null
}

export function ProfilePage({ teamId, dateRange }: ProfilePageProps) {
  const { user } = useAuth()
  const engineerId = user?.engineer_id ?? ""
  const [searchParams, setSearchParams] = useSearchParams()
  const rawTab = searchParams.get("tab")
  const activeTab: TabId = rawTab && validTabIds.has(rawTab) ? (rawTab as TabId) : "overview"

  const startDate = dateRange?.startDate
  const endDate = dateRange?.endDate
  const { data: profile, isLoading } = useEngineerProfile(engineerId, startDate, endDate)

  const handleTabChange = (tab: TabId) => {
    setSearchParams(tab === "overview" ? {} : { tab })
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <CardSkeleton />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      </div>
    )
  }

  if (!profile) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">
        Unable to load your profile. Please try again.
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6 lg:flex-row lg:gap-8">
      {/* Left sidebar */}
      <div className="lg:w-72 lg:shrink-0">
        <ProfileSidebar profile={profile} />
      </div>

      {/* Right content */}
      <div className="min-w-0 flex-1">
        <PageTabs tabs={tabs} activeTab={activeTab} onChange={handleTabChange} />

        <div className="mt-6">
          {activeTab === "overview" && (
            <ProfileOverviewTab
              engineerId={engineerId}
              teamId={teamId}
              startDate={startDate}
              endDate={endDate}
            />
          )}
          {activeTab === "sessions" && (
            <ProfileSessionsTab
              engineerId={engineerId}
              teamId={teamId}
              dateRange={dateRange}
            />
          )}
          {activeTab === "insights" && (
            <ProfileInsightsTab
              profile={profile}
              teamId={teamId}
              startDate={startDate}
              endDate={endDate}
            />
          )}
          {activeTab === "growth" && (
            <ProfileGrowthTab
              profile={profile}
              teamId={teamId}
              startDate={startDate}
              endDate={endDate}
            />
          )}
        </div>
      </div>
    </div>
  )
}
