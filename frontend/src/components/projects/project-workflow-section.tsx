import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatDuration, formatNumber, formatPercent, titleize } from "@/lib/utils"
import type { ProjectWorkflowSummary } from "@/types/api"

interface ProjectWorkflowSectionProps {
  workflowSummary: ProjectWorkflowSummary
}

export function ProjectWorkflowSection({ workflowSummary }: ProjectWorkflowSectionProps) {
  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Workflow Fingerprints</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Coverage</p>
              <p className="mt-1 font-display text-2xl">
                {formatPercent(workflowSummary.coverage_pct)}
              </p>
            </div>
            <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">
                Fingerprinted Sessions
              </p>
              <p className="mt-1 font-display text-2xl">
                {formatNumber(workflowSummary.fingerprinted_sessions)}
              </p>
            </div>
            <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">
                Total Sessions
              </p>
              <p className="mt-1 font-display text-2xl">
                {formatNumber(workflowSummary.total_sessions)}
              </p>
            </div>
          </div>

          {workflowSummary.fingerprints.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Not enough session structure yet to infer project workflows.
            </p>
          ) : (
            <div className="space-y-3">
              {workflowSummary.fingerprints.map((fingerprint) => (
                <div
                  key={fingerprint.fingerprint_id}
                  className="rounded-xl border border-border/60 bg-background p-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-1">
                      <p className="font-medium capitalize">{fingerprint.label}</p>
                      <p className="text-sm text-muted-foreground">
                        {formatNumber(fingerprint.session_count)} sessions
                        {" • "}
                        {formatPercent(fingerprint.share_of_sessions)} of project activity
                        {" • "}
                        {fingerprint.avg_duration_seconds != null
                          ? formatDuration(fingerprint.avg_duration_seconds)
                          : "-"}
                        {" avg"}
                      </p>
                    </div>
                    <Badge variant="secondary">
                      Success {formatPercent(fingerprint.success_rate)}
                    </Badge>
                  </div>

                  <div className="mt-3 flex flex-wrap gap-2">
                    {fingerprint.steps.map((step) => (
                      <Badge key={step} variant="outline" className="capitalize">
                        {titleize(step)}
                      </Badge>
                    ))}
                  </div>

                  <div className="mt-3 grid gap-3 lg:grid-cols-2">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        Top Tools
                      </p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {fingerprint.top_tools.length === 0 ? (
                          <span className="text-sm text-muted-foreground">No tool telemetry</span>
                        ) : (
                          fingerprint.top_tools.map((tool) => (
                            <Badge key={tool} variant="secondary">
                              {tool}
                            </Badge>
                          ))
                        )}
                      </div>
                    </div>

                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        Friction Signals
                      </p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {fingerprint.top_friction_types.length === 0 ? (
                          <span className="text-sm text-muted-foreground">No repeated frictions</span>
                        ) : (
                          fingerprint.top_friction_types.map((friction) => (
                            <Badge key={friction} variant="secondary" className="capitalize">
                              {titleize(friction)}
                            </Badge>
                          ))
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Friction Hotspots</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {workflowSummary.friction_hotspots.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No workflow-linked hotspots detected for this project yet.
            </p>
          ) : (
            workflowSummary.friction_hotspots.map((hotspot) => (
              <div
                key={hotspot.friction_type}
                className="rounded-xl border border-border/60 bg-background p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="space-y-1">
                    <p className="font-medium capitalize">{titleize(hotspot.friction_type)}</p>
                    <p className="text-sm text-muted-foreground">
                      {formatNumber(hotspot.session_count)} sessions
                      {" • "}
                      {formatPercent(hotspot.share_of_sessions)} of project sessions
                    </p>
                  </div>
                  <div className="text-right text-sm text-muted-foreground">
                    <p>{formatNumber(hotspot.total_occurrences)} occurrences</p>
                    <p>
                      Success penalty{" "}
                      {hotspot.impact_score != null ? formatPercent(hotspot.impact_score) : "-"}
                    </p>
                  </div>
                </div>

                <div className="mt-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Linked Workflows
                  </p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {hotspot.linked_fingerprints.map((label) => (
                      <Badge key={label} variant="outline" className="capitalize">
                        {label}
                      </Badge>
                    ))}
                  </div>
                </div>

                {hotspot.sample_details.length > 0 && (
                  <div className="mt-3 space-y-2">
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Sample Evidence
                    </p>
                    {hotspot.sample_details.map((detail) => (
                      <p
                        key={detail}
                        className="rounded-lg bg-muted/40 px-3 py-2 text-sm text-muted-foreground"
                      >
                        {detail}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  )
}
