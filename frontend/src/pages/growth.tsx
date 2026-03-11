import { useEffect, useMemo, useState } from "react"
import { GraduationCap, UserRoundSearch } from "lucide-react"
import { useSearchParams } from "react-router-dom"
import {
  useEngineerProfile,
  useEngineers,
  useOnboardingAcceleration,
  usePatternSharing,
  useSkillInventory,
  useLearningPaths,
} from "@/hooks/use-api-queries"
import { useAuth } from "@/lib/auth-context"
import { getApiKey } from "@/lib/api"
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
import { WorkflowPlaybookCards } from "@/components/growth/workflow-playbook-cards"
import { EngineerSkillTable } from "@/components/insights/engineer-skill-table"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import type { DateRange } from "@/components/layout/date-range-picker"

const tabs = [
  { id: "onboarding", label: "Onboarding" },
  { id: "patterns", label: "Patterns" },
  { id: "skills", label: "Skills" },
  { id: "playbooks", label: "Playbooks" },
] as const

type TabId = (typeof tabs)[number]["id"]
const PROFILE_ENGINEER_STORAGE_KEY = "primer_profile_engineer_id"

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

function PlaybooksTab({ startDate, endDate }: Omit<TabProps, "teamId">) {
  const { user } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const isApiKeyUser = !user && !!getApiKey()
  const rawEngineerId = searchParams.get("engineer_id")
  const rememberedEngineerId =
    isApiKeyUser && typeof window !== "undefined"
      ? window.localStorage.getItem(PROFILE_ENGINEER_STORAGE_KEY) ?? ""
      : ""
  const engineerId = user?.engineer_id ?? rawEngineerId ?? rememberedEngineerId

  const { data: profile, isLoading } = useEngineerProfile(engineerId, startDate, endDate)
  const { data: engineers, isLoading: loadingEngineers } = useEngineers(false, isApiKeyUser)

  useEffect(() => {
    if (!isApiKeyUser || !rawEngineerId || typeof window === "undefined") return
    window.localStorage.setItem(PROFILE_ENGINEER_STORAGE_KEY, rawEngineerId)
  }, [isApiKeyUser, rawEngineerId])

  const selectableEngineers = useMemo(
    () =>
      (engineers ?? [])
        .filter((engineer) => engineer.is_active)
        .sort((a, b) =>
          (a.display_name ?? a.name).localeCompare(b.display_name ?? b.name),
        ),
    [engineers],
  )

  const handleEngineerSelect = (nextEngineerId: string) => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(PROFILE_ENGINEER_STORAGE_KEY, nextEngineerId)
    }
    const nextParams = new URLSearchParams(searchParams)
    nextParams.set("engineer_id", nextEngineerId)
    setSearchParams(nextParams)
  }

  const handleEngineerReset = () => {
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(PROFILE_ENGINEER_STORAGE_KEY)
    }
    const nextParams = new URLSearchParams(searchParams)
    nextParams.delete("engineer_id")
    setSearchParams(nextParams)
  }

  if (isLoading || (isApiKeyUser && !engineerId && loadingEngineers)) {
    return <ChartSkeleton />
  }

  if (isApiKeyUser && !engineerId) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <UserRoundSearch className="h-4 w-4" />
            Choose an engineer for playbooks
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Workflow playbooks are personalized from peer patterns, so pick an engineer context to
            see the right recommendations.
          </p>

          {selectableEngineers.length === 0 ? (
            <p className="text-sm text-muted-foreground">No active engineers are available.</p>
          ) : (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {selectableEngineers.map((engineer) => (
                <button
                  key={engineer.id}
                  type="button"
                  onClick={() => handleEngineerSelect(engineer.id)}
                  className="rounded-xl border border-border/60 bg-card p-4 text-left transition-colors hover:bg-accent hover:text-accent-foreground"
                >
                  <p className="font-medium">{engineer.display_name ?? engineer.name}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{engineer.email}</p>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    )
  }

  if (!profile) {
    return (
      <Card>
        <CardContent className="space-y-3 p-6 text-sm text-muted-foreground">
          <p>Primer could not load workflow playbooks for the current engineer context.</p>
          {isApiKeyUser && (
            <div>
              <Button variant="outline" onClick={handleEngineerReset}>
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
          <Button variant="outline" size="sm" onClick={handleEngineerReset}>
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
