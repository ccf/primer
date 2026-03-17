import { useState } from "react"
import { Link, useParams } from "react-router-dom"
import { ArrowLeft } from "lucide-react"
import { useEngineerProfile } from "@/hooks/use-api-queries"
import { PageTabs } from "@/components/ui/page-tabs"
import { ProfileSidebar } from "@/components/shared/profile-sidebar"
import { TrajectorySparklines } from "@/components/engineer-profile/trajectory-sparklines"
import { FrictionTab } from "@/components/engineer-profile/friction-tab"
import { StrengthsTab } from "@/components/engineer-profile/strengths-tab"
import { QualityTab } from "@/components/engineer-profile/quality-tab"
import { InsightsReport } from "@/components/engineer-profile/insights-report"
import { CardSkeleton } from "@/components/shared/loading-skeleton"
import type { DateRange } from "@/components/layout/date-range-picker"

const tabs = [
  { id: "insights", label: "Insights" },
  { id: "friction", label: "Friction" },
  { id: "strengths", label: "Strengths" },
  { id: "quality", label: "Quality" },
] as const

type TabId = (typeof tabs)[number]["id"]

interface EngineerProfilePageProps {
  dateRange: DateRange | null
}

export function EngineerProfilePage({ dateRange }: EngineerProfilePageProps) {
  const { id } = useParams<{ id: string }>()
  const engineerId = id ?? ""
  const startDate = dateRange?.startDate
  const endDate = dateRange?.endDate

  const { data: profile, isLoading } = useEngineerProfile(engineerId, startDate, endDate)
  const [activeTab, setActiveTab] = useState<TabId>("insights")

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
      <Link
        to="/engineers"
        className="group inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-0.5" />
        Back to engineers
      </Link>

      <div className="flex flex-col gap-6 lg:flex-row lg:gap-8">
        {/* Left sidebar */}
        <div className="lg:w-72 lg:shrink-0">
          <ProfileSidebar profile={profile} />
        </div>

        {/* Right content */}
        <div className="min-w-0 flex-1">
          <PageTabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

          <div className="mt-6">
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
              />
            )}
            {activeTab === "quality" && (
              <QualityTab quality={profile.quality} />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
