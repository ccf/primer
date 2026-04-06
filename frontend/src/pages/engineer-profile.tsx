import { Link, useParams, useSearchParams } from "react-router-dom"
import { ArrowLeft } from "lucide-react"
import { useEngineerProfile } from "@/hooks/use-api-queries"
import { useAuth } from "@/lib/auth-context"
import { PageTabs } from "@/components/ui/page-tabs"
import { ProfileSidebar } from "@/components/shared/profile-sidebar"
import { PersonalImpactReview } from "@/components/insights/personal-impact-review"
import { TrajectorySparklines } from "@/components/engineer-profile/trajectory-sparklines"
import { FrictionTab } from "@/components/engineer-profile/friction-tab"
import { StrengthsTab } from "@/components/engineer-profile/strengths-tab"
import { QualityTab } from "@/components/engineer-profile/quality-tab"
import { InsightsReport } from "@/components/engineer-profile/insights-report"
import { ProfileSessionsTab } from "@/components/profile/profile-sessions-tab"
import { ProfileGrowthTab } from "@/components/profile/profile-growth-tab"
import { CardSkeleton } from "@/components/shared/loading-skeleton"
import type { DateRange } from "@/components/layout/date-range-picker"

const tabs = [
  { id: "impact", label: "Impact" },
  { id: "insights", label: "Insights" },
  { id: "sessions", label: "Sessions" },
  { id: "friction", label: "Friction" },
  { id: "strengths", label: "Strengths" },
  { id: "quality", label: "Quality" },
  { id: "growth", label: "Growth" },
] as const

type TabId = (typeof tabs)[number]["id"]

const validTabIds = new Set<string>(tabs.map((t) => t.id))

interface EngineerProfilePageProps {
  teamId?: string | null
  dateRange: DateRange | null
}

export function EngineerProfilePage({ teamId, dateRange }: EngineerProfilePageProps) {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const engineerId = id ?? ""
  const startDate = dateRange?.startDate
  const endDate = dateRange?.endDate
  const isOwnProfile = user?.engineer_id === engineerId

  const [searchParams, setSearchParams] = useSearchParams()
  const rawTab = searchParams.get("tab")
  const activeTab: TabId = rawTab && validTabIds.has(rawTab) ? (rawTab as TabId) : "impact"

  const { data: profile, isLoading } = useEngineerProfile(engineerId, startDate, endDate)

  const handleTabChange = (tab: TabId) => {
    const nextParams = new URLSearchParams()
    if (tab !== "impact") nextParams.set("tab", tab)
    setSearchParams(nextParams)
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
        <CardSkeleton />
      </div>
    )
  }

  if (!profile) {
    return (
      <div className="space-y-4">
        <Link
          to="/engineers"
          className="group inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-0.5" />
          Back to engineers
        </Link>
        <div className="py-8 text-center text-sm text-muted-foreground">
          Engineer profile not found.
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {!isOwnProfile && (
        <Link
          to="/engineers"
          className="group inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-0.5" />
          Back to engineers
        </Link>
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
            {activeTab === "impact" && (
              <PersonalImpactReview profile={profile} />
            )}
            {activeTab === "insights" && (
              <>
                <TrajectorySparklines data={profile.weekly_trajectory} />
                <div className="mt-8">
                  <InsightsReport
                    profile={profile}
                    engineerId={engineerId}
                    startDate={startDate}
                    endDate={endDate}
                  />
                </div>
              </>
            )}
            {activeTab === "sessions" && (
              <ProfileSessionsTab
                engineerId={engineerId}
                teamId={teamId ?? null}
                dateRange={dateRange}
              />
            )}
            {activeTab === "friction" && (
              <FrictionTab
                friction={profile.friction}
                configSuggestions={profile.config_suggestions}
              />
            )}
            {activeTab === "strengths" && (
              <StrengthsTab
                strengths={profile.strengths}
                learningPaths={profile.learning_paths}
                toolRecommendations={profile.tool_recommendations}
                modelRecommendations={profile.model_recommendations}
              />
            )}
            {activeTab === "quality" && (
              <QualityTab quality={profile.quality} />
            )}
            {activeTab === "growth" && (
              <ProfileGrowthTab
                profile={profile}
                teamId={teamId ?? null}
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
