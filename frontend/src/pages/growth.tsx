import { useState } from "react"
import { cn } from "@/lib/utils"
import {
  useLearningPaths,
  usePatternSharing,
  useOnboardingAcceleration,
} from "@/hooks/use-api-queries"
import { CoverageSummary } from "@/components/growth/coverage-summary"
import { LearningPathCards } from "@/components/growth/learning-path-cards"
import { SkillUniverseChart } from "@/components/growth/skill-universe-chart"
import { PatternSummary } from "@/components/growth/pattern-summary"
import { SharedPatternCards } from "@/components/growth/shared-pattern-card"
import { CohortComparison } from "@/components/growth/cohort-comparison"
import { NewHireTable } from "@/components/growth/new-hire-table"
import { OnboardingRecommendations } from "@/components/growth/onboarding-recommendations"
import { VelocityChart } from "@/components/growth/velocity-chart"
import { CardSkeleton } from "@/components/shared/loading-skeleton"
import type { DateRange } from "@/components/layout/date-range-picker"

const tabs = [
  { id: "learning", label: "Learning Paths" },
  { id: "patterns", label: "Pattern Sharing" },
  { id: "onboarding", label: "Onboarding" },
] as const

type TabId = (typeof tabs)[number]["id"]

interface GrowthPageProps {
  teamId: string | null
  dateRange: DateRange | null
}

export function GrowthPage({ teamId, dateRange }: GrowthPageProps) {
  const [activeTab, setActiveTab] = useState<TabId>("learning")
  const startDate = dateRange?.startDate
  const endDate = dateRange?.endDate

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Growth</h1>

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

      {activeTab === "learning" && (
        <LearningTab teamId={teamId} startDate={startDate} endDate={endDate} />
      )}
      {activeTab === "patterns" && (
        <PatternsTab teamId={teamId} startDate={startDate} endDate={endDate} />
      )}
      {activeTab === "onboarding" && (
        <OnboardingTab teamId={teamId} startDate={startDate} endDate={endDate} />
      )}
    </div>
  )
}

function LearningTab({ teamId, startDate, endDate }: { teamId: string | null; startDate?: string; endDate?: string }) {
  const { data, isLoading } = useLearningPaths(teamId, startDate, endDate)

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
        <CardSkeleton />
      </div>
    )
  }

  if (!data || data.sessions_analyzed === 0) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">
        No session data available for learning path analysis.
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <CoverageSummary data={data} />
      <LearningPathCards paths={data.engineer_paths} />
      <SkillUniverseChart universe={data.team_skill_universe} />
    </div>
  )
}

function PatternsTab({ teamId, startDate, endDate }: { teamId: string | null; startDate?: string; endDate?: string }) {
  const { data, isLoading } = usePatternSharing(teamId, startDate, endDate)

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
        <CardSkeleton />
      </div>
    )
  }

  if (!data || data.sessions_analyzed === 0) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">
        No session data available for pattern analysis.
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PatternSummary data={data} />
      <SharedPatternCards patterns={data.patterns} />
    </div>
  )
}

function OnboardingTab({ teamId, startDate, endDate }: { teamId: string | null; startDate?: string; endDate?: string }) {
  const { data, isLoading } = useOnboardingAcceleration(teamId, startDate, endDate)

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
        <CardSkeleton />
      </div>
    )
  }

  if (!data || data.sessions_analyzed === 0) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">
        No session data available for onboarding analysis.
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <CohortComparison cohorts={data.cohorts} />
      <NewHireTable progress={data.new_hire_progress} />
      <VelocityChart progress={data.new_hire_progress} />
      <OnboardingRecommendations recommendations={data.recommendations} />
    </div>
  )
}
