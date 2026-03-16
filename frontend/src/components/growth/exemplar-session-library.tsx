import { Link } from "react-router-dom"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatCost, formatDuration, formatLabel, formatPercent, titleize } from "@/lib/utils"
import type { ExemplarSession } from "@/types/api"

interface ExemplarSessionLibraryProps {
  exemplars: ExemplarSession[]
}

export function ExemplarSessionLibrary({ exemplars }: ExemplarSessionLibraryProps) {
  if (exemplars.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">
        No exemplar sessions identified yet.
      </div>
    )
  }

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      {exemplars.map((exemplar) => (
        <Card key={exemplar.exemplar_id}>
          <CardHeader className="pb-3">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1">
                <CardTitle className="text-base">{exemplar.title}</CardTitle>
                <p className="text-sm text-muted-foreground">{exemplar.summary}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                {exemplar.workflow_archetype && (
                  <Badge variant="success">{formatLabel(exemplar.workflow_archetype)}</Badge>
                )}
                {exemplar.project_name && (
                  <Badge variant="outline">{exemplar.project_name}</Badge>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-4">
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Support</p>
                <p className="mt-1 font-display text-2xl">{exemplar.supporting_engineer_count}</p>
                <p className="text-xs text-muted-foreground">
                  {exemplar.supporting_session_count} sessions
                </p>
              </div>
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Success</p>
                <p className="mt-1 font-display text-2xl">{formatPercent(exemplar.success_rate)}</p>
              </div>
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Duration</p>
                <p className="mt-1 font-display text-2xl">{formatDuration(exemplar.duration_seconds)}</p>
              </div>
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Cost</p>
                <p className="mt-1 font-display text-2xl">
                  {exemplar.estimated_cost != null ? formatCost(exemplar.estimated_cost) : "-"}
                </p>
              </div>
            </div>

            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Why This Exemplar
              </p>
              <p className="text-sm text-muted-foreground">{exemplar.why_selected}</p>
            </div>

            {exemplar.session_summary && (
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Session Summary
                </p>
                <p className="text-sm text-muted-foreground">{exemplar.session_summary}</p>
              </div>
            )}

            <div className="grid gap-4 lg:grid-cols-2">
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Workflow Evidence
                </p>
                <div className="flex flex-wrap gap-2">
                  {exemplar.workflow_fingerprint ? (
                    <Badge variant="secondary">{exemplar.workflow_fingerprint}</Badge>
                  ) : (
                    <span className="text-sm text-muted-foreground">No workflow fingerprint yet</span>
                  )}
                  {exemplar.workflow_steps.map((step) => (
                    <Badge key={step} variant="outline">
                      {titleize(step)}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Exemplar Tools
                </p>
                <div className="flex flex-wrap gap-2">
                  {exemplar.tools_used.length === 0 ? (
                    <span className="text-sm text-muted-foreground">No tool telemetry</span>
                  ) : (
                    exemplar.tools_used.map((tool) => (
                      <Badge key={tool} variant="secondary">
                        {tool}
                      </Badge>
                    ))
                  )}
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Linked Patterns
              </p>
              <div className="flex flex-wrap gap-2">
                {exemplar.linked_patterns.map((pattern) => (
                  <Badge key={pattern.cluster_id} variant="outline">
                    {pattern.cluster_label}
                  </Badge>
                ))}
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border/60 bg-background p-4">
              <div className="space-y-1">
                <p className="font-medium">{exemplar.engineer_name}</p>
                <p className="text-sm text-muted-foreground">
                  {exemplar.outcome ? formatLabel(exemplar.outcome) : "Outcome unknown"}
                  {exemplar.helpfulness ? ` • ${formatLabel(exemplar.helpfulness)}` : ""}
                </p>
              </div>
              <Link
                to={`/sessions/${exemplar.session_id}`}
                className="text-sm font-medium text-primary hover:underline"
              >
                Open exemplar
              </Link>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
