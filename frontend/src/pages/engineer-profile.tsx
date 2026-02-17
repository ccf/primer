import { useState } from "react"
import { Link, useParams } from "react-router-dom"
import { ArrowLeft, Activity, CheckCircle2, DollarSign, Clock } from "lucide-react"
import { cn, formatNumber, formatCost, formatPercent, formatDuration } from "@/lib/utils"
import { useEngineerProfile } from "@/hooks/use-api-queries"
import { StatCard } from "@/components/dashboard/stat-card"
import { TrajectorySparklines } from "@/components/engineer-profile/trajectory-sparklines"
import { FrictionTab } from "@/components/engineer-profile/friction-tab"
import { StrengthsTab } from "@/components/engineer-profile/strengths-tab"
import { QualityTab } from "@/components/engineer-profile/quality-tab"
import { CardSkeleton } from "@/components/shared/loading-skeleton"
import type { DateRange } from "@/components/layout/date-range-picker"

const tabs = [
  { id: "trajectory", label: "Trajectory" },
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
  const [activeTab, setActiveTab] = useState<TabId>("trajectory")

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

      {/* Header */}
      <div className="flex items-center gap-4">
        {profile.avatar_url ? (
          <img
            src={profile.avatar_url}
            alt={profile.name}
            className="h-14 w-14 rounded-full"
          />
        ) : (
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-muted text-lg font-medium">
            {profile.name.charAt(0)}
          </div>
        )}
        <div>
          <h1 className="text-2xl font-bold">
            {profile.display_name ?? profile.name}
          </h1>
          <p className="text-sm text-muted-foreground">{profile.email}</p>
          {profile.team_name && (
            <p className="text-xs text-muted-foreground">Team: {profile.team_name}</p>
          )}
        </div>
      </div>

      {/* Overview stat cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Sessions"
          value={formatNumber(overview.total_sessions)}
          icon={Activity}
        />
        <StatCard
          label="Success Rate"
          value={formatPercent(overview.success_rate)}
          icon={CheckCircle2}
        />
        <StatCard
          label="Estimated Cost"
          value={overview.estimated_cost != null ? formatCost(overview.estimated_cost) : "-"}
          icon={DollarSign}
        />
        <StatCard
          label="Avg Duration"
          value={formatDuration(overview.avg_session_duration)}
          icon={Clock}
        />
      </div>

      {/* Tabs */}
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

      {/* Tab content */}
      {activeTab === "trajectory" && (
        <TrajectorySparklines data={profile.weekly_trajectory} />
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
  )
}
