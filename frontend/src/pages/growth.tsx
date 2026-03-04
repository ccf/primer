import { useState } from "react"
import { GraduationCap } from "lucide-react"
import {
  useOnboardingAcceleration,
  usePatternSharing,
  useSkillInventory,
  useLearningPaths,
} from "@/hooks/use-api-queries"
import { PageTabs } from "@/components/ui/page-tabs"
import { PageHeader } from "@/components/shared/page-header"
import { ChartSkeleton } from "@/components/shared/loading-skeleton"
import { CohortComparison } from "@/components/growth/cohort-comparison"
import { NewHireTable } from "@/components/growth/new-hire-table"
import { VelocityChart } from "@/components/growth/velocity-chart"
import { OnboardingRecommendations } from "@/components/growth/onboarding-recommendations"
import { PatternSummary } from "@/components/growth/pattern-summary"
import { SharedPatternCards } from "@/components/growth/shared-pattern-card"
import { SkillInventorySummary } from "@/components/insights/skill-inventory-summary"
import { CoverageSummary } from "@/components/growth/coverage-summary"
import { TeamSkillGaps } from "@/components/insights/team-skill-gaps"
import { SkillUniverseChart } from "@/components/growth/skill-universe-chart"
import { EngineerSkillTable } from "@/components/insights/engineer-skill-table"
import type { DateRange } from "@/components/layout/date-range-picker"

const tabs = [
  { id: "onboarding", label: "Onboarding" },
  { id: "patterns", label: "Patterns" },
  { id: "skills", label: "Skills" },
] as const

type TabId = (typeof tabs)[number]["id"]

interface TabProps {
  teamId: string | null
  startDate?: string
  endDate?: string
}

function OnboardingTab({ teamId, startDate, endDate }: TabProps) {
  const { data, isLoading } = useOnboardingAcceleration(teamId, startDate, endDate)
  if (isLoading) return <ChartSkeleton />
  if (!data) return null
  return (
    <div className="space-y-6">
      <CohortComparison cohorts={data.cohorts} />
      <div className="grid gap-6 lg:grid-cols-2">
        <NewHireTable progress={data.new_hire_progress} />
        <VelocityChart progress={data.new_hire_progress} />
      </div>
      <OnboardingRecommendations recommendations={data.recommendations} />
    </div>
  )
}

function PatternsTab({ teamId, startDate, endDate }: TabProps) {
  const { data, isLoading } = usePatternSharing(teamId, startDate, endDate)
  if (isLoading) return <ChartSkeleton />
  if (!data) return null
  return (
    <div className="space-y-6">
      <PatternSummary data={data} />
      <SharedPatternCards patterns={data.patterns} />
    </div>
  )
}

function SkillsTab({ teamId, startDate, endDate }: TabProps) {
  const { data: skills, isLoading: loadingSkills } = useSkillInventory(teamId, startDate, endDate)
  const { data: learning, isLoading: loadingLearning } = useLearningPaths(teamId, startDate, endDate)
  if (loadingSkills || loadingLearning) return <ChartSkeleton />
  return (
    <div className="space-y-6">
      {skills && learning && (
        <div className="grid gap-6 lg:grid-cols-2">
          <SkillInventorySummary data={skills} />
          <CoverageSummary data={learning} />
        </div>
      )}
      {skills && learning && (
        <div className="grid gap-6 lg:grid-cols-2">
          <TeamSkillGaps data={skills.team_skill_gaps} />
          <SkillUniverseChart universe={learning.team_skill_universe} />
        </div>
      )}
      {skills && <EngineerSkillTable data={skills.engineer_profiles} />}
    </div>
  )
}

interface GrowthPageProps {
  teamId: string | null
  dateRange: DateRange | null
}

export function GrowthPage({ teamId, dateRange }: GrowthPageProps) {
  const [activeTab, setActiveTab] = useState<TabId>("onboarding")
  const startDate = dateRange?.startDate
  const endDate = dateRange?.endDate

  return (
    <div className="space-y-6">
      <PageHeader
        icon={GraduationCap}
        title="Growth & Skills"
        description="Onboarding acceleration, shared patterns, and skill development"
      />

      <PageTabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      {activeTab === "onboarding" && <OnboardingTab teamId={teamId} startDate={startDate} endDate={endDate} />}
      {activeTab === "patterns" && <PatternsTab teamId={teamId} startDate={startDate} endDate={endDate} />}
      {activeTab === "skills" && <SkillsTab teamId={teamId} startDate={startDate} endDate={endDate} />}
    </div>
  )
}
