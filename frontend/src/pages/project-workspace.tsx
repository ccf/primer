import { Link, useParams } from "react-router-dom"
import {
  ArrowLeft,
  FolderKanban,
  GitPullRequest,
  MonitorDot,
} from "lucide-react"
import { useProjectWorkspace } from "@/hooks/use-api-queries"
import { PageHeader } from "@/components/shared/page-header"
import { CardSkeleton, ChartSkeleton } from "@/components/shared/loading-skeleton"
import { ProjectScorecard } from "@/components/projects/project-scorecard"
import { ProjectEnablementCard } from "@/components/projects/project-enablement-card"
import { ProjectRepositoriesCard } from "@/components/projects/project-repositories-card"
import { ProjectWorkflowSection } from "@/components/projects/project-workflow-section"
import { PRTable } from "@/components/quality/pr-table"
import { QualityAttributionTable } from "@/components/quality/quality-attribution-table"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatCost, formatDuration, formatNumber, formatPercent, formatTokens } from "@/lib/utils"
import type { DateRange } from "@/components/layout/date-range-picker"

interface ProjectWorkspacePageProps {
  teamId: string | null
  dateRange: DateRange | null
}

export function ProjectWorkspacePage({ teamId, dateRange }: ProjectWorkspacePageProps) {
  const { projectName: rawProjectName } = useParams<{ projectName: string }>()
  const projectName = rawProjectName ?? ""
  const startDate = dateRange?.startDate
  const endDate = dateRange?.endDate
  const { data, isLoading, error } = useProjectWorkspace(projectName, teamId, startDate, endDate)

  if (isLoading) {
    return (
      <div className="space-y-6">
        <CardSkeleton />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          {Array.from({ length: 5 }).map((_, index) => (
            <CardSkeleton key={index} />
          ))}
        </div>
        <ChartSkeleton />
        <ChartSkeleton />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        <Link
          to="/projects"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Projects
        </Link>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Project not found</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Primer could not find a project named <span className="font-medium">{projectName}</span> in the
              current scope.
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  const outcomeEntries = Object.entries(data.project.outcome_distribution).sort((a, b) => b[1] - a[1])

  return (
    <div className="space-y-8">
      <Link
        to="/projects"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Projects
      </Link>

      <PageHeader
        icon={FolderKanban}
        title={data.project.project_name}
        description={`${formatNumber(data.project.total_sessions)} sessions • ${formatNumber(data.project.unique_engineers)} engineers • ${formatCost(data.project.estimated_cost)} spend`}
      >
        <Link to={`/sessions?project=${encodeURIComponent(data.project.project_name)}`}>
          <Button variant="outline" size="sm">
            <MonitorDot className="mr-1 h-4 w-4" />
            View Sessions
          </Button>
        </Link>
      </PageHeader>

      <ProjectScorecard scorecard={data.scorecard} overview={data.overview} />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Project Overview</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Messages</p>
                <p className="mt-1 font-display text-2xl">{formatNumber(data.overview.total_messages)}</p>
              </div>
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Tool Calls</p>
                <p className="mt-1 font-display text-2xl">{formatNumber(data.overview.total_tool_calls)}</p>
              </div>
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Tracked Tokens</p>
                <p className="mt-1 font-display text-2xl">
                  {formatTokens(data.overview.total_input_tokens + data.overview.total_output_tokens)}
                </p>
              </div>
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Avg Duration</p>
                <p className="mt-1 font-display text-2xl">{formatDuration(data.overview.avg_session_duration)}</p>
              </div>
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <div className="space-y-2">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Outcomes
                </h3>
                {outcomeEntries.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No facet outcomes recorded yet.</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {outcomeEntries.map(([outcome, count]) => (
                      <Badge key={outcome} variant="secondary" className="gap-1">
                        <span className="capitalize">{outcome}</span>
                        <span className="text-muted-foreground">{count}</span>
                      </Badge>
                    ))}
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Session Health
                </h3>
                <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                  <p className="font-display text-2xl">
                    {data.overview.avg_health_score != null ? data.overview.avg_health_score.toFixed(1) : "-"}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Composite score from outcomes, friction, duration, and satisfaction where available.
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <ProjectEnablementCard
          enablement={data.enablement}
          teamId={teamId}
          projectName={data.project.project_name}
          startDate={startDate}
          endDate={endDate}
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <ProjectRepositoriesCard repositories={data.repositories} />

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Friction</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {data.friction ? (
              <>
                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">Friction Rate</p>
                    <p className="mt-1 font-display text-2xl">{formatPercent(data.friction.friction_rate)}</p>
                  </div>
                  <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">Affected Sessions</p>
                    <p className="mt-1 font-display text-2xl">{formatNumber(data.friction.sessions_with_friction)}</p>
                  </div>
                  <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">Total Frictions</p>
                    <p className="mt-1 font-display text-2xl">{formatNumber(data.friction.total_friction_count)}</p>
                  </div>
                </div>

                <div className="space-y-2">
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Top Friction Types
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {data.friction.top_friction_types.map((item) => (
                      <Badge key={item} variant="secondary">{item.replaceAll("_", " ")}</Badge>
                    ))}
                  </div>
                </div>

                <div className="space-y-2">
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Highest Impact Patterns
                  </h3>
                  {data.friction_impacts.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No friction impact clusters yet.</p>
                  ) : (
                    <div className="space-y-2">
                      {data.friction_impacts.map((impact) => (
                        <div
                          key={impact.friction_type}
                          className="rounded-xl border border-border/60 p-3"
                        >
                          <div className="flex items-center justify-between gap-4">
                            <p className="font-medium">{impact.friction_type.replaceAll("_", " ")}</p>
                            <p className="text-sm text-muted-foreground">
                              {formatPercent(impact.success_rate_with)} with friction
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">
                No project-scoped friction telemetry yet.
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      <ProjectWorkflowSection workflowSummary={data.workflow_summary} />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Cost View</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Total Spend</p>
                <p className="mt-1 font-display text-2xl">{formatCost(data.cost.total_estimated_cost)}</p>
              </div>
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Avg Cost / Session</p>
                <p className="mt-1 font-display text-2xl">{data.scorecard.avg_cost_per_session != null ? formatCost(data.scorecard.avg_cost_per_session) : "-"}</p>
              </div>
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Cost / Success</p>
                <p className="mt-1 font-display text-2xl">{data.scorecard.cost_per_successful_outcome != null ? formatCost(data.scorecard.cost_per_successful_outcome) : "-"}</p>
              </div>
            </div>

            {data.cost.model_breakdown.length === 0 ? (
              <p className="text-sm text-muted-foreground">No model-usage telemetry yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left text-muted-foreground">
                      <th className="pb-2 font-medium">Model</th>
                      <th className="pb-2 text-right font-medium">Input</th>
                      <th className="pb-2 text-right font-medium">Output</th>
                      <th className="pb-2 text-right font-medium">Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.cost.model_breakdown.slice(0, 5).map((model) => (
                      <tr key={model.model_name} className="border-b border-border/40 last:border-0">
                        <td className="py-2">{model.model_name}</td>
                        <td className="py-2 text-right">{formatTokens(model.input_tokens)}</td>
                        <td className="py-2 text-right">{formatTokens(model.output_tokens)}</td>
                        <td className="py-2 text-right">{formatCost(model.estimated_cost)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Quality View</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">PRs</p>
                <p className="mt-1 font-display text-2xl">{formatNumber(data.quality.overview.total_prs)}</p>
              </div>
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">PR Merge Rate</p>
                <p className="mt-1 font-display text-2xl">{formatPercent(data.quality.overview.pr_merge_rate)}</p>
              </div>
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Findings</p>
                <p className="mt-1 font-display text-2xl">{formatNumber(data.quality.findings_overview?.total_findings ?? 0)}</p>
              </div>
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Fix Rate</p>
                <p className="mt-1 font-display text-2xl">{formatPercent(data.quality.findings_overview?.fix_rate)}</p>
              </div>
            </div>

            <p className="text-sm text-muted-foreground">
              Project quality is scoped to PRs directly linked to this project’s sessions, so the workspace stays attribution-safe.
            </p>
          </CardContent>
        </Card>
      </div>

      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-muted-foreground">Linked Pull Requests</h2>
        {data.quality.recent_prs.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-sm text-muted-foreground">
              No project-linked pull requests yet.
            </CardContent>
          </Card>
        ) : (
          <PRTable prs={data.quality.recent_prs} />
        )}
      </section>

      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <GitPullRequest className="h-4 w-4 text-primary" />
          <h2 className="text-sm font-semibold text-muted-foreground">Quality Attribution</h2>
        </div>
        <Card>
          <CardContent className="pt-6">
            <QualityAttributionTable rows={data.quality.attribution} />
          </CardContent>
        </Card>
      </section>
    </div>
  )
}
