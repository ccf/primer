import { useSearchParams } from "react-router-dom"
import { useEngineerProfile } from "@/hooks/use-api-queries"
import { useEngineerChooser } from "@/hooks/use-engineer-chooser"
import { PageTabs } from "@/components/ui/page-tabs"
import { EngineerChooserCard } from "@/components/shared/engineer-chooser-card"
import { ProfileSidebar } from "@/components/shared/profile-sidebar"
import { ProfileOverviewTab } from "@/components/profile/profile-overview-tab"
import { ProfileSessionsTab } from "@/components/profile/profile-sessions-tab"
import { ProfileInsightsTab } from "@/components/profile/profile-insights-tab"
import { ProfileGrowthTab } from "@/components/profile/profile-growth-tab"
import { CardSkeleton } from "@/components/shared/loading-skeleton"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
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
  const [searchParams, setSearchParams] = useSearchParams()
  const rawTab = searchParams.get("tab")
  const rawEngineerId = searchParams.get("engineer_id")
  const activeTab: TabId = rawTab && validTabIds.has(rawTab) ? (rawTab as TabId) : "overview"
  const {
    isApiKeyUser,
    engineerId,
    selectableEngineers,
    loadingEngineers,
    selectEngineer,
    resetEngineer,
  } = useEngineerChooser({
    rawEngineerId,
    createSearchParams: (nextEngineerId) => {
      const nextParams = new URLSearchParams()
      if (activeTab !== "overview") nextParams.set("tab", activeTab)
      if (nextEngineerId) nextParams.set("engineer_id", nextEngineerId)
      return nextParams
    },
    setSearchParams,
  })

  const startDate = dateRange?.startDate
  const endDate = dateRange?.endDate
  const { data: profile, isLoading } = useEngineerProfile(engineerId, startDate, endDate)

  const handleTabChange = (tab: TabId) => {
    const nextParams = new URLSearchParams()
    if (tab !== "overview") nextParams.set("tab", tab)
    if (isApiKeyUser && engineerId) nextParams.set("engineer_id", engineerId)
    setSearchParams(nextParams)
  }

  if (isLoading || (isApiKeyUser && !engineerId && loadingEngineers)) {
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

  if (isApiKeyUser && !engineerId) {
    return (
      <div className="space-y-6">
        <EngineerChooserCard
          title="Choose a profile"
          description="Admin API-key sessions do not have a personal engineer identity. Pick an engineer to view their profile, growth tab, and workflow playbooks."
          engineers={selectableEngineers}
          onSelect={selectEngineer}
        />
      </div>
    )
  }

  if (!profile) {
    return (
      <div className="space-y-4 py-8 text-center text-sm text-muted-foreground">
        <div>Unable to load your profile. Please try again.</div>
        {isApiKeyUser && (
          <div>
            <Button variant="outline" onClick={resetEngineer}>
              Choose another engineer
            </Button>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {isApiKeyUser && (
        <Card>
          <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium">Viewing engineer profile context</p>
              <p className="text-sm text-muted-foreground">
                {profile.display_name ?? profile.name} ({profile.email})
              </p>
            </div>
            <Button variant="outline" size="sm" onClick={resetEngineer}>
              Change engineer
            </Button>
          </CardContent>
        </Card>
      )}

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
    </div>
  )
}
