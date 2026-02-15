import { useState } from "react"
import { cn } from "@/lib/utils"
import {
  useConfigOptimization,
  usePersonalizedTips,
  useSkillInventory,
} from "@/hooks/use-api-queries"
import { ConfigSuggestionsList } from "@/components/insights/config-suggestions-list"
import { PersonalizedTipsList } from "@/components/insights/personalized-tips-list"
import { SkillInventorySummary } from "@/components/insights/skill-inventory-summary"
import { EngineerSkillTable } from "@/components/insights/engineer-skill-table"
import { TeamSkillGaps } from "@/components/insights/team-skill-gaps"
import { CardSkeleton } from "@/components/shared/loading-skeleton"
import type { DateRange } from "@/components/layout/date-range-picker"

const tabs = [
  { id: "config", label: "Config Optimization" },
  { id: "tips", label: "Personalized Tips" },
  { id: "skills", label: "Skill Inventory" },
] as const

type TabId = (typeof tabs)[number]["id"]

interface InsightsPageProps {
  teamId: string | null
  dateRange: DateRange | null
}

export function InsightsPage({ teamId, dateRange }: InsightsPageProps) {
  const [activeTab, setActiveTab] = useState<TabId>("config")
  const startDate = dateRange?.startDate
  const endDate = dateRange?.endDate

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Insights</h1>

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

      {activeTab === "config" && (
        <ConfigTab teamId={teamId} startDate={startDate} endDate={endDate} />
      )}
      {activeTab === "tips" && (
        <TipsTab teamId={teamId} startDate={startDate} endDate={endDate} />
      )}
      {activeTab === "skills" && (
        <SkillsTab teamId={teamId} startDate={startDate} endDate={endDate} />
      )}
    </div>
  )
}

function ConfigTab({ teamId, startDate, endDate }: { teamId: string | null; startDate?: string; endDate?: string }) {
  const { data, isLoading } = useConfigOptimization(teamId, startDate, endDate)

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <CardSkeleton key={i} />
        ))}
      </div>
    )
  }

  return (
    <ConfigSuggestionsList
      suggestions={data?.suggestions ?? []}
      sessionsAnalyzed={data?.sessions_analyzed ?? 0}
    />
  )
}

function TipsTab({ teamId, startDate, endDate }: { teamId: string | null; startDate?: string; endDate?: string }) {
  const { data, isLoading } = usePersonalizedTips(teamId, startDate, endDate)

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <CardSkeleton key={i} />
        ))}
      </div>
    )
  }

  return (
    <PersonalizedTipsList
      tips={data?.tips ?? []}
      sessionsAnalyzed={data?.sessions_analyzed ?? 0}
    />
  )
}

function SkillsTab({ teamId, startDate, endDate }: { teamId: string | null; startDate?: string; endDate?: string }) {
  const { data, isLoading } = useSkillInventory(teamId, startDate, endDate)

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

  if (!data || data.total_engineers === 0) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">
        No skill data available yet.
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <SkillInventorySummary data={data} />
      <EngineerSkillTable data={data.engineer_profiles} />
      <TeamSkillGaps data={data.team_skill_gaps} />
    </div>
  )
}
