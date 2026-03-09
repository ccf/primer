import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useUpdateIntervention } from "@/hooks/use-api-mutations"
import { formatCost, formatPercent, timeAgo } from "@/lib/utils"
import type {
  EngineerResponse,
  InterventionMetricsSnapshot,
  InterventionResponse,
  InterventionStatus,
} from "@/types/api"

interface InterventionCardProps {
  intervention: InterventionResponse
  ownerOptions: EngineerResponse[]
  canManage: boolean
  canManageOwner: boolean
}

const severityVariant = {
  critical: "destructive",
  warning: "warning",
  info: "info",
} as const

const statusVariant: Record<InterventionStatus, "outline" | "info" | "warning" | "success"> = {
  planned: "outline",
  in_progress: "warning",
  completed: "success",
  dismissed: "info",
}

function formatStatus(status: InterventionStatus) {
  return status.replaceAll("_", " ")
}

function formatMetricDelta(
    baseline: number | null | undefined,
    current: number | null | undefined,
    formatter: (value: number | null | undefined) => string,
) {
  if (baseline == null && current == null) return "-"
  if (current == null) return `${formatter(baseline)} baseline`
  return `${formatter(baseline)} -> ${formatter(current)}`
}

function metricValue(label: string, baseline: InterventionMetricsSnapshot | null, current: InterventionMetricsSnapshot | null) {
  switch (label) {
    case "Success rate":
      return formatMetricDelta(baseline?.success_rate, current?.success_rate, formatPercent)
    case "Avg cost / session":
      return formatMetricDelta(
        baseline?.avg_cost_per_session,
        current?.avg_cost_per_session,
        (value) => (value == null ? "-" : formatCost(value)),
      )
    case "Friction events":
      return formatMetricDelta(
        baseline?.friction_events,
        current?.friction_events,
        (value) => (value == null ? "-" : String(value)),
      )
    case "Findings / PR":
      return formatMetricDelta(
        baseline?.findings_per_pr,
        current?.findings_per_pr,
        (value) => (value == null ? "-" : value.toFixed(1)),
      )
    default:
      return "-"
  }
}

export function InterventionCard({
  intervention,
  ownerOptions,
  canManage,
  canManageOwner,
}: InterventionCardProps) {
  const updateIntervention = useUpdateIntervention()
  const evidenceEntries = Object.entries(intervention.evidence ?? {}).slice(0, 3)
  const scopeBits = [
    intervention.project_name ? `Project ${intervention.project_name}` : null,
    intervention.engineer?.name ? `Engineer ${intervention.engineer.name}` : null,
    intervention.team_name ? `Team ${intervention.team_name}` : null,
    !intervention.project_name && !intervention.engineer && !intervention.team_name
      ? "Organization"
      : null,
  ].filter(Boolean)
  const hasCurrentMetrics = intervention.current_metrics != null

  function patch(payload: {
    status?: InterventionStatus
    due_date?: string | null
    owner_engineer_id?: string | null
  }) {
    updateIntervention.mutate({ id: intervention.id, ...payload })
  }

  return (
    <Card className="border-border/60">
      <CardHeader className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={severityVariant[intervention.severity as keyof typeof severityVariant] ?? "info"}>
                {intervention.severity}
              </Badge>
              <Badge variant={statusVariant[intervention.status]}>{formatStatus(intervention.status)}</Badge>
              <Badge variant="outline">{intervention.category}</Badge>
            </div>
            <CardTitle className="text-base">{intervention.title}</CardTitle>
            <p className="max-w-3xl text-sm text-muted-foreground">{intervention.description}</p>
          </div>

          <div className="text-right text-xs text-muted-foreground">
            <p>Updated {timeAgo(intervention.updated_at)}</p>
            {intervention.source_title && <p className="mt-1">{intervention.source_title}</p>}
          </div>
        </div>

        <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
          {scopeBits.map((bit) => (
            <span key={bit} className="rounded-full bg-muted px-2.5 py-1">
              {bit}
            </span>
          ))}
          <span className="rounded-full bg-muted px-2.5 py-1">
            Owner {intervention.owner_engineer?.name ?? "Unassigned"}
          </span>
          <span className="rounded-full bg-muted px-2.5 py-1">
            Due {intervention.due_date ?? "Not set"}
          </span>
        </div>
      </CardHeader>

      <CardContent className="space-y-5">
        {canManage && (
          <div className="grid gap-4 rounded-xl border border-border/60 bg-muted/20 p-4 sm:grid-cols-3">
            <div className="space-y-2">
              <label className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Status
              </label>
              <select
                value={intervention.status}
                onChange={(event) =>
                  patch({ status: event.target.value as InterventionStatus })
                }
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none transition-colors focus:border-primary"
              >
                <option value="planned">Planned</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
                <option value="dismissed">Dismissed</option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Due Date
              </label>
              <input
                type="date"
                value={intervention.due_date ?? ""}
                onChange={(event) => patch({ due_date: event.target.value || null })}
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none transition-colors focus:border-primary"
              />
            </div>

            <div className="space-y-2">
              <label className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Owner
              </label>
              <select
                value={intervention.owner_engineer_id ?? ""}
                onChange={(event) =>
                  patch({ owner_engineer_id: event.target.value || null })
                }
                disabled={!canManageOwner}
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none transition-colors focus:border-primary disabled:opacity-60"
              >
                <option value="">Unassigned</option>
                {ownerOptions.map((engineer) => (
                  <option key={engineer.id} value={engineer.id}>
                    {engineer.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}

        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <section className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-sm font-semibold text-muted-foreground">Before / After</h3>
              {!hasCurrentMetrics && (
                <p className="text-xs text-muted-foreground">
                  Current impact recalculates on direct updates.
                </p>
              )}
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {["Success rate", "Avg cost / session", "Friction events", "Findings / PR"].map((label) => (
                <div key={label} className="rounded-xl border border-border/60 bg-background p-3">
                  <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    {label}
                  </p>
                  <p className="mt-2 text-sm font-medium">
                    {metricValue(label, intervention.baseline_metrics, intervention.current_metrics)}
                  </p>
                </div>
              ))}
            </div>
          </section>

          <section className="space-y-3">
            <h3 className="text-sm font-semibold text-muted-foreground">Evidence</h3>
            <div className="rounded-xl border border-border/60 bg-background p-4">
              {evidenceEntries.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No linked evidence was captured for this intervention yet.
                </p>
              ) : (
                <dl className="space-y-2 text-sm">
                  {evidenceEntries.map(([key, value]) => (
                    <div key={key} className="flex items-start justify-between gap-4">
                      <dt className="text-muted-foreground">{key.replaceAll("_", " ")}</dt>
                      <dd className="text-right font-medium">
                        {typeof value === "number" ? value : String(value)}
                      </dd>
                    </div>
                  ))}
                </dl>
              )}
            </div>
          </section>
        </div>
      </CardContent>
    </Card>
  )
}
