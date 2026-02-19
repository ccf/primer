import { useState } from "react"
import { Link, useParams } from "react-router-dom"
import { ArrowLeft } from "lucide-react"
import { formatNumber, formatCost, formatPercent, formatDuration } from "@/lib/utils"
import { useEngineerProfile, useNarrative, useNarrativeStatus } from "@/hooks/use-api-queries"
import { InlineStat } from "@/components/ui/inline-stat"
import { PageTabs } from "@/components/ui/page-tabs"
import { TrajectorySparklines } from "@/components/engineer-profile/trajectory-sparklines"
import { FrictionTab } from "@/components/engineer-profile/friction-tab"
import { StrengthsTab } from "@/components/engineer-profile/strengths-tab"
import { QualityTab } from "@/components/engineer-profile/quality-tab"
import { NarrativeReport } from "@/components/narrative/narrative-report"
import { NarrativeSkeleton } from "@/components/narrative/narrative-skeleton"
import { useRefreshNarrative } from "@/hooks/use-api-mutations"
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
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to engineers
        </Link>
        <div className="py-8 text-center text-sm text-muted-foreground">
          Engineer profile not found.
        </div>
      </div>
    )
  }

  const overview = profile.overview

  return (
    <div className="space-y-6">
      <Link
        to="/engineers"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to engineers
      </Link>

      <div className="flex gap-8">
        {/* Left sidebar */}
        <div className="w-72 shrink-0">
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

          <div className="mt-4">
            <h1 className="text-xl font-semibold">{profile.display_name ?? profile.name}</h1>
            {profile.github_username && (
              <p className="text-sm text-muted-foreground">@{profile.github_username}</p>
            )}
            <p className="mt-1 text-sm text-muted-foreground">{profile.email}</p>
          </div>

          <div className="mt-6 grid grid-cols-2 gap-4">
            <InlineStat label="Sessions" value={formatNumber(overview.total_sessions)} />
            <InlineStat label="Success Rate" value={formatPercent(overview.success_rate)} />
            <InlineStat
              label="Est. Cost"
              value={overview.estimated_cost != null ? formatCost(overview.estimated_cost) : "-"}
            />
            <InlineStat label="Avg Duration" value={formatDuration(overview.avg_session_duration)} />
            {profile.leverage_score != null && (
              <InlineStat label="Leverage" value={profile.leverage_score.toFixed(1)} />
            )}
          </div>

          {profile.team_name && (
            <div className="mt-6">
              <span className="inline-flex items-center rounded-full border border-border px-3 py-1 text-xs font-medium">
                {profile.team_name}
              </span>
            </div>
          )}

          {profile.projects.length > 0 && (
            <div className="mt-4">
              <p className="mb-2 text-xs font-medium text-muted-foreground">Projects</p>
              <div className="flex flex-wrap gap-1.5">
                {profile.projects.slice(0, 8).map((p) => (
                  <span
                    key={p}
                    className="inline-flex items-center rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium"
                  >
                    {p}
                  </span>
                ))}
                {profile.projects.length > 8 && (
                  <span className="inline-flex items-center rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
                    +{profile.projects.length - 8} more
                  </span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Right content */}
        <div className="min-w-0 flex-1">
          <PageTabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

          <div className="mt-6">
            {activeTab === "insights" && (
              <>
                <TrajectorySparklines data={profile.weekly_trajectory} />
                <div className="mt-8">
                  <ProfileNarrativeSection
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

function ProfileNarrativeSection({
  engineerId,
  startDate,
  endDate,
}: {
  engineerId: string
  startDate?: string
  endDate?: string
}) {
  const { data: status } = useNarrativeStatus()
  const { data, isLoading, error } = useNarrative(
    "engineer",
    undefined,
    startDate,
    endDate,
    status?.available !== false,
    engineerId,
  )

  const refreshMutation = useRefreshNarrative()

  const handleRefresh = () => {
    refreshMutation.mutate({
      scope: "engineer",
      startDate,
      endDate,
      engineerId,
    })
  }

  if (status?.available === false) return null
  if (isLoading || refreshMutation.isPending) return <NarrativeSkeleton />
  if (error) {
    if (String(error).includes("422") || String(error).includes("Insufficient")) {
      return (
        <p className="py-4 text-center text-sm text-muted-foreground">
          Not enough session data for narrative synthesis yet.
        </p>
      )
    }
    return null
  }
  if (!data) return null

  return (
    <NarrativeReport
      data={refreshMutation.data ?? data}
      onRefresh={handleRefresh}
      isRefreshing={refreshMutation.isPending}
    />
  )
}
