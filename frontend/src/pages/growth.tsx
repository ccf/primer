import { useState } from "react"
import { GraduationCap } from "lucide-react"
import { useSearchParams } from "react-router-dom"
import {
  useEngineerProfile,
  useOnboardingAcceleration,
  usePatternSharing,
  useSkillInventory,
  useLearningPaths,
} from "@/hooks/use-api-queries"
import { useEngineerChooser } from "@/hooks/use-engineer-chooser"
import { PageTabs } from "@/components/ui/page-tabs"
import { EngineerChooserCard } from "@/components/shared/engineer-chooser-card"
import { PageHeader } from "@/components/shared/page-header"
import { ChartSkeleton } from "@/components/shared/loading-skeleton"
import { CohortComparison } from "@/components/growth/cohort-comparison"
import { NewHireTable } from "@/components/growth/new-hire-table"
import { VelocityChart } from "@/components/growth/velocity-chart"
import { OnboardingRecommendations } from "@/components/growth/onboarding-recommendations"
import { PatternSummary } from "@/components/growth/pattern-summary"
import { BrightSpotCards } from "@/components/growth/bright-spot-cards"
import { SharedPatternCards } from "@/components/growth/shared-pattern-card"
import { SkillInventorySummary } from "@/components/insights/skill-inventory-summary"
import { CoverageSummary } from "@/components/growth/coverage-summary"
import { TeamSkillGaps } from "@/components/insights/team-skill-gaps"
import { SkillUniverseChart } from "@/components/growth/skill-universe-chart"
import { WorkflowPlaybookCards } from "@/components/growth/workflow-playbook-cards"
import { EngineerSkillTable } from "@/components/insights/engineer-skill-table"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import type { DateRange } from "@/components/layout/date-range-picker"

const tabs = [
  { id: "onboarding", label: "Onboarding" },
  { id: "patterns", label: "Patterns" },
  { id: "skills", label: "Skills" },
  { id: "playbooks", label: "Playbooks" },
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
      <BrightSpotCards spots={data.bright_spots} />
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

function PlaybooksTab({ startDate, endDate }: Omit<TabProps, "teamId">) {
  const [searchParams, setSearchParams] = useSearchParams()
  const rawEngineerId = searchParams.get("engineer_id")
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
      const nextParams = new URLSearchParams(searchParams)
      if (nextEngineerId) {
        nextParams.set("engineer_id", nextEngineerId)
      } else {
        nextParams.delete("engineer_id")
      }
      return nextParams
    },
    setSearchParams,
  })

  const { data: profile, isLoading } = useEngineerProfile(engineerId, startDate, endDate)

  if (isLoading || (isApiKeyUser && !engineerId && loadingEngineers)) {
    return <ChartSkeleton />
  }

  if (isApiKeyUser && !engineerId) {
    return (
      <EngineerChooserCard
        title="Choose an engineer for playbooks"
        description="Workflow playbooks are personalized from peer patterns, so pick an engineer context to see the right recommendations."
        engineers={selectableEngineers}
        onSelect={selectEngineer}
      />
    )
  }

  if (!profile) {
    return (
      <Card>
        <CardContent className="space-y-3 p-6 text-sm text-muted-foreground">
          <p>Primer could not load workflow playbooks for the current engineer context.</p>
          {isApiKeyUser && (
            <div>
              <Button variant="outline" onClick={resetEngineer}>
                Choose another engineer
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <h3 className="text-sm font-medium">Workflow Playbooks</h3>
        <p className="text-sm text-muted-foreground">
          Reusable high-performing patterns learned from peer sessions for{" "}
          {profile.display_name ?? profile.name}.
        </p>
      </div>

      {isApiKeyUser && (
        <div>
          <Button variant="outline" size="sm" onClick={resetEngineer}>
            Change engineer
          </Button>
        </div>
      )}

      <WorkflowPlaybookCards playbooks={profile.workflow_playbooks} />
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
      {activeTab === "playbooks" && <PlaybooksTab startDate={startDate} endDate={endDate} />}
    </div>
  )
}
