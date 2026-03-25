import { useMemo, useState } from "react"
import { ArrowLeftRight, Scale } from "lucide-react"

import {
  useCompareAnalytics,
  useEngineers,
  useProjectAnalytics,
  useTeams,
} from "@/hooks/use-api-queries"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { PageHeader } from "@/components/shared/page-header"
import { PageTabs } from "@/components/ui/page-tabs"
import { CardSkeleton } from "@/components/shared/loading-skeleton"
import { Badge } from "@/components/ui/badge"
import {
  formatCost,
  formatLabel,
  formatPercent,
} from "@/lib/utils"
import type { CompareResponse } from "@/types/api"
import type { DateRange } from "@/components/layout/date-range-picker"

type CompareMode = "team" | "engineer" | "project" | "period"

const compareTabs = [
  { id: "team", label: "Teams" },
  { id: "engineer", label: "Engineers" },
  { id: "project", label: "Projects" },
  { id: "period", label: "Periods" },
] as const

interface ComparePageProps {
  teamId: string | null
  dateRange: DateRange | null
}

function resolvePair(options: string[], left: string, right: string) {
  const effectiveLeft = options.includes(left) ? left : (options[0] ?? "")
  const effectiveRight =
    options.includes(right) && right !== effectiveLeft
      ? right
      : (options.find((option) => option !== effectiveLeft) ?? "")
  return { effectiveLeft, effectiveRight }
}

function formatSigned(value: number | null | undefined, formatter: (value: number) => string) {
  if (value == null) return "-"
  const sign = value > 0 ? "+" : value < 0 ? "-" : ""
  return `${sign}${formatter(Math.abs(value))}`
}

function formatDeltaPercent(value: number | null | undefined) {
  if (value == null) return "-"
  const points = value * 100
  const sign = points > 0 ? "+" : points < 0 ? "-" : ""
  return `${sign}${Math.abs(points).toFixed(0)} pts`
}

function SnapshotCard({
  title,
  data,
}: {
  title: string
  data: CompareResponse["left"]
}) {
  const metrics = [
    { label: "Sessions", value: data.total_sessions.toLocaleString() },
    { label: "Success Rate", value: formatPercent(data.success_rate) },
    { label: "Total Cost", value: data.total_cost != null ? formatCost(data.total_cost) : "-" },
    {
      label: "Cost / Success",
      value:
        data.cost_per_successful_outcome != null
          ? formatCost(data.cost_per_successful_outcome)
          : "-",
    },
    {
      label: "Effectiveness",
      value: data.effectiveness_score != null ? data.effectiveness_score.toFixed(1) : "-",
    },
    {
      label: "Leverage",
      value: data.leverage_score != null ? data.leverage_score.toFixed(1) : "-",
    },
  ]

  return (
    <Card className="overflow-hidden">
      <div className="h-1 bg-gradient-to-r from-primary/70 via-primary/20 to-transparent" />
      <CardHeader>
        <CardTitle className="text-lg">{title}</CardTitle>
        <CardDescription>{data.label}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {metrics.map((metric) => (
            <div
              key={metric.label}
              className="rounded-2xl border border-border/60 bg-muted/20 p-4"
            >
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                {metric.label}
              </p>
              <p className="mt-3 font-display text-3xl tracking-tight">{metric.value}</p>
            </div>
          ))}
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-foreground">Top Workflows</h3>
            <span className="text-xs text-muted-foreground">
              {data.top_workflows.length} pattern{data.top_workflows.length === 1 ? "" : "s"}
            </span>
          </div>
          {data.top_workflows.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No workflow signal is available for this selection yet.
            </p>
          ) : (
            <div className="grid gap-3 md:grid-cols-3">
              {data.top_workflows.map((workflow) => (
                <div
                  key={`${data.label}:${workflow.label}`}
                  className="rounded-2xl border border-border/60 bg-background p-4"
                >
                  <p className="font-medium">{formatLabel(workflow.label)}</p>
                  <div className="mt-3 flex items-center justify-between text-sm text-muted-foreground">
                    <span>{workflow.session_count} sessions</span>
                    <Badge variant="outline">{formatPercent(workflow.share_of_sessions)}</Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

function DeltaStrip({ data }: { data: CompareResponse["delta"] }) {
  const metrics = [
    {
      label: "Success Delta",
      value: formatDeltaPercent(data.success_rate),
    },
    {
      label: "Cost / Success Delta",
      value: formatSigned(data.cost_per_successful_outcome, formatCost),
    },
    {
      label: "Effectiveness Delta",
      value:
        data.effectiveness_score != null
          ? `${data.effectiveness_score > 0 ? "+" : ""}${data.effectiveness_score.toFixed(1)}`
          : "-",
    },
    {
      label: "Leverage Delta",
      value:
        data.leverage_score != null
          ? `${data.leverage_score > 0 ? "+" : ""}${data.leverage_score.toFixed(1)}`
          : "-",
    },
  ]

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {metrics.map((metric) => (
        <div
          key={metric.label}
          className="rounded-2xl border border-border/60 bg-muted/20 p-4"
        >
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
            {metric.label}
          </p>
          <p className="mt-3 font-display text-3xl tracking-tight">{metric.value}</p>
        </div>
      ))}
    </div>
  )
}

export function ComparePage({ teamId, dateRange }: ComparePageProps) {
  const [mode, setMode] = useState<CompareMode>("team")
  const [leftTeamId, setLeftTeamId] = useState("")
  const [rightTeamId, setRightTeamId] = useState("")
  const [leftEngineerId, setLeftEngineerId] = useState("")
  const [rightEngineerId, setRightEngineerId] = useState("")
  const [leftProjectName, setLeftProjectName] = useState("")
  const [rightProjectName, setRightProjectName] = useState("")

  const startDate = dateRange?.startDate
  const endDate = dateRange?.endDate

  const { data: teams = [] } = useTeams()
  const { data: engineers = [] } = useEngineers()
  const { data: projectsData } = useProjectAnalytics(teamId, startDate, endDate)

  const teamOptions = teams
  const engineerOptions = useMemo(
    () =>
      engineers.filter((engineer) => (teamId ? engineer.team_id === teamId : true)),
    [engineers, teamId],
  )
  const projectOptions = useMemo(
    () => (projectsData?.projects ?? []).map((project) => project.project_name),
    [projectsData],
  )

  const { effectiveLeft: effectiveLeftTeamId, effectiveRight: effectiveRightTeamId } = resolvePair(
    teamOptions.map((team) => team.id),
    leftTeamId,
    rightTeamId,
  )
  const {
    effectiveLeft: effectiveLeftEngineerId,
    effectiveRight: effectiveRightEngineerId,
  } = resolvePair(
    engineerOptions.map((engineer) => engineer.id),
    leftEngineerId,
    rightEngineerId,
  )
  const {
    effectiveLeft: effectiveLeftProjectName,
    effectiveRight: effectiveRightProjectName,
  } = resolvePair(projectOptions, leftProjectName, rightProjectName)

  const compareEnabled =
    mode === "period" ||
    (
      mode === "team" &&
      !!effectiveLeftTeamId &&
      !!effectiveRightTeamId &&
      effectiveLeftTeamId !== effectiveRightTeamId
    ) ||
    (mode === "engineer" &&
      !!effectiveLeftEngineerId &&
      !!effectiveRightEngineerId &&
      effectiveLeftEngineerId !== effectiveRightEngineerId) ||
    (mode === "project" &&
      !!effectiveLeftProjectName &&
      !!effectiveRightProjectName &&
      effectiveLeftProjectName !== effectiveRightProjectName)

  const compare = useCompareAnalytics({
    mode,
    leftKey:
      mode === "team"
        ? effectiveLeftTeamId
        : mode === "engineer"
          ? effectiveLeftEngineerId
          : mode === "project"
            ? effectiveLeftProjectName
            : undefined,
    rightKey:
      mode === "team"
        ? effectiveRightTeamId
        : mode === "engineer"
          ? effectiveRightEngineerId
          : mode === "project"
            ? effectiveRightProjectName
            : undefined,
    teamId: mode === "project" || mode === "period" ? teamId : undefined,
    startDate,
    endDate,
    enabled: compareEnabled,
  })

  return (
    <div className="space-y-8">
      <PageHeader
        icon={Scale}
        title="Compare"
        description="Put teams, engineers, projects, and periods side by side across the signals that matter."
      />

      <PageTabs tabs={compareTabs} activeTab={mode} onChange={(tab) => setMode(tab as CompareMode)} />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Compare Selections</CardTitle>
          <CardDescription>
            Choose the two things you want to put side by side. Period mode compares the current window with the previous matching window.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {mode === "team" && (
            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-1">
                <span className="text-sm font-medium">Team A</span>
                <select
                  value={effectiveLeftTeamId}
                  onChange={(e) => setLeftTeamId(e.target.value)}
                  className="h-10 w-full rounded-xl border border-input bg-background px-3 text-sm"
                >
                  {teamOptions.map((team) => (
                    <option key={team.id} value={team.id}>
                      {team.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="space-y-1">
                <span className="text-sm font-medium">Team B</span>
                <select
                  value={effectiveRightTeamId}
                  onChange={(e) => setRightTeamId(e.target.value)}
                  className="h-10 w-full rounded-xl border border-input bg-background px-3 text-sm"
                >
                  {teamOptions.map((team) => (
                    <option key={team.id} value={team.id}>
                      {team.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          )}

          {mode === "engineer" && (
            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-1">
                <span className="text-sm font-medium">Engineer A</span>
                <select
                  value={effectiveLeftEngineerId}
                  onChange={(e) => setLeftEngineerId(e.target.value)}
                  className="h-10 w-full rounded-xl border border-input bg-background px-3 text-sm"
                >
                  {engineerOptions.map((engineer) => (
                    <option key={engineer.id} value={engineer.id}>
                      {engineer.display_name ?? engineer.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="space-y-1">
                <span className="text-sm font-medium">Engineer B</span>
                <select
                  value={effectiveRightEngineerId}
                  onChange={(e) => setRightEngineerId(e.target.value)}
                  className="h-10 w-full rounded-xl border border-input bg-background px-3 text-sm"
                >
                  {engineerOptions.map((engineer) => (
                    <option key={engineer.id} value={engineer.id}>
                      {engineer.display_name ?? engineer.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          )}

          {mode === "project" && (
            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-1">
                <span className="text-sm font-medium">Project A</span>
                <select
                  value={effectiveLeftProjectName}
                  onChange={(e) => setLeftProjectName(e.target.value)}
                  className="h-10 w-full rounded-xl border border-input bg-background px-3 text-sm"
                >
                  {projectOptions.map((project) => (
                    <option key={project} value={project}>
                      {project}
                    </option>
                  ))}
                </select>
              </label>
              <label className="space-y-1">
                <span className="text-sm font-medium">Project B</span>
                <select
                  value={effectiveRightProjectName}
                  onChange={(e) => setRightProjectName(e.target.value)}
                  className="h-10 w-full rounded-xl border border-input bg-background px-3 text-sm"
                >
                  {projectOptions.map((project) => (
                    <option key={project} value={project}>
                      {project}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          )}

          {mode === "period" && (
            <div className="rounded-2xl border border-border/60 bg-muted/20 p-4 text-sm text-muted-foreground">
              <div className="flex items-center gap-2 text-foreground">
                <ArrowLeftRight className="h-4 w-4 text-primary" />
                <span className="font-medium">Selected period vs previous period</span>
              </div>
              <p className="mt-2">
                {startDate && endDate
                  ? "Using the current date filter from the app header and comparing it to the immediately previous matching window."
                  : "No date range is selected, so compare mode uses the most recent 30-day window versus the 30 days before it."}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {!compareEnabled ? (
        <Card>
          <CardContent className="p-8 text-center text-sm text-muted-foreground">
            Choose two distinct selections to start comparing.
          </CardContent>
        </Card>
      ) : compare.isLoading ? (
        <div className="grid gap-6 xl:grid-cols-2">
          <CardSkeleton />
          <CardSkeleton />
        </div>
      ) : compare.data ? (
        <div className="space-y-6">
          <DeltaStrip data={compare.data.delta} />
          <div className="grid gap-6 xl:grid-cols-2">
            <SnapshotCard title="A" data={compare.data.left} />
            <SnapshotCard title="B" data={compare.data.right} />
          </div>
        </div>
      ) : (
        <Card>
          <CardContent className="p-8 text-center text-sm text-muted-foreground">
            Compare data is not available for the current selections yet.
          </CardContent>
        </Card>
      )}
    </div>
  )
}
