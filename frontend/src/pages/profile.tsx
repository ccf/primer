import { useSearchParams } from "react-router-dom"
import { useAuth } from "@/lib/auth-context"
import { useEngineerProfile } from "@/hooks/use-api-queries"
import { InlineStat } from "@/components/ui/inline-stat"
import { PageTabs } from "@/components/ui/page-tabs"
import { ProfileOverviewTab } from "@/components/profile/profile-overview-tab"
import { ProfileSessionsTab } from "@/components/profile/profile-sessions-tab"
import { ProfileInsightsTab } from "@/components/profile/profile-insights-tab"
import { ProfileGrowthTab } from "@/components/profile/profile-growth-tab"
import { CardSkeleton } from "@/components/shared/loading-skeleton"
import { formatNumber, formatPercent, formatCost, formatDuration } from "@/lib/utils"
import type { DateRange } from "@/components/layout/date-range-picker"

const tabs = [
  { id: "overview", label: "Overview" },
  { id: "sessions", label: "Sessions" },
  { id: "insights", label: "Insights" },
  { id: "growth", label: "Growth" },
] as const

type TabId = (typeof tabs)[number]["id"]

interface ProfilePageProps {
  teamId: string | null
  dateRange: DateRange | null
}

export function ProfilePage({ teamId, dateRange }: ProfilePageProps) {
  const { user } = useAuth()
  const engineerId = user?.engineer_id ?? ""
  const [searchParams, setSearchParams] = useSearchParams()
  const activeTab = (searchParams.get("tab") as TabId) || "overview"

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

  const overview = profile.overview

  return (
    <div className="flex gap-8">
      {/* Left sidebar */}
      <div className="w-72 shrink-0">
        {/* Avatar */}
        {profile.avatar_url ? (
          <img
            src={profile.avatar_url}
            alt={profile.display_name ?? profile.name}
            className="h-48 w-48 rounded-full"
          />
        ) : (
          <div className="flex h-48 w-48 items-center justify-center rounded-full bg-muted text-4xl font-medium">
            {(profile.display_name ?? profile.name).charAt(0).toUpperCase()}
          </div>
        )}

        {/* Name */}
        <div className="mt-4">
          <h1 className="text-xl font-semibold">{profile.display_name ?? profile.name}</h1>
          {profile.github_username && (
            <p className="text-sm text-muted-foreground">@{profile.github_username}</p>
          )}
          <p className="mt-1 text-sm text-muted-foreground">{profile.email}</p>
        </div>

        {/* Stats grid */}
        <div className="mt-6 grid grid-cols-2 gap-4">
          <InlineStat label="Sessions" value={formatNumber(overview.total_sessions)} />
          <InlineStat label="Success Rate" value={formatPercent(overview.success_rate)} />
          <InlineStat
            label="Est. Cost"
            value={overview.estimated_cost != null ? formatCost(overview.estimated_cost) : "-"}
          />
          <InlineStat label="Avg Duration" value={formatDuration(overview.avg_session_duration)} />
        </div>

        {/* Team badge */}
        {profile.team_name && (
          <div className="mt-6">
            <span className="inline-flex items-center rounded-full border border-border px-3 py-1 text-xs font-medium">
              {profile.team_name}
            </span>
          </div>
        )}
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
