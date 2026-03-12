import { BadgeCheck, ShieldAlert, ShieldCheck } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { formatCost, formatPercent } from "@/lib/utils"
import type { AgentType, CrossProjectComparisonEntry, CrossProjectComparisonResponse } from "@/types/api"

interface ProjectComparisonCardProps {
  comparison: CrossProjectComparisonResponse
}

const AGENT_LABELS: Record<AgentType, string> = {
  claude_code: "Claude Code",
  codex_cli: "Codex CLI",
  gemini_cli: "Gemini CLI",
  cursor: "Cursor",
}

function formatEffectiveness(value: number | null | undefined): string {
  if (value == null) return "-"
  return value.toFixed(1)
}

function ComparisonColumn({
  title,
  subtitle,
  rows,
}: {
  title: string
  subtitle: string
  rows: CrossProjectComparisonEntry[]
}) {
  if (rows.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-border/70 bg-muted/20 p-4">
        <div className="space-y-1">
          <h3 className="text-sm font-semibold">{title}</h3>
          <p className="text-sm text-muted-foreground">{subtitle}</p>
        </div>
        <p className="mt-4 text-sm text-muted-foreground">
          Primer does not have enough scored project data yet to rank this list.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-3 rounded-2xl border border-border/70 bg-card/70 p-4">
      <div className="space-y-1">
        <h3 className="text-sm font-semibold">{title}</h3>
        <p className="text-sm text-muted-foreground">{subtitle}</p>
      </div>

      <div className="space-y-3">
        {rows.map((row) => (
          <div
            key={row.project_name}
            className="rounded-xl border border-border/60 bg-muted/20 p-3"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-medium">{row.project_name}</p>
                <p className="text-xs text-muted-foreground">
                  {row.total_sessions} sessions • {row.unique_engineers} engineers
                </p>
              </div>
              <div className="text-right">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">
                  Effectiveness
                </p>
                <p className="font-display text-2xl">{formatEffectiveness(row.effectiveness_score)}</p>
              </div>
            </div>

            <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
              <Badge variant="secondary">Success {formatPercent(row.effectiveness_rate)}</Badge>
              <Badge variant="secondary">Quality {formatPercent(row.quality_rate)}</Badge>
              <Badge variant="secondary">Friction {formatPercent(row.friction_rate)}</Badge>
              <Badge variant="secondary">
                Confidence {formatPercent(row.measurement_confidence)}
              </Badge>
              <Badge variant="secondary">
                Readiness{" "}
                {row.ai_readiness_score != null ? row.ai_readiness_score.toFixed(0) : "-"}
              </Badge>
              <Badge variant="secondary">
                Cost {row.avg_cost_per_session != null ? formatCost(row.avg_cost_per_session) : "-"}
              </Badge>
              <Badge variant="secondary">
                Agent{" "}
                {row.dominant_agent_type ? AGENT_LABELS[row.dominant_agent_type] : "Unknown"}
              </Badge>
            </div>

            {row.top_recommendation_title ? (
              <p className="mt-3 text-sm text-muted-foreground">{row.top_recommendation_title}</p>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  )
}

export function ProjectComparisonCard({ comparison }: ProjectComparisonCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Cross-Project Comparison</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Compared Projects</p>
            <p className="mt-1 font-display text-2xl">{comparison.compared_projects}</p>
          </div>
          <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Best AI Fit</p>
            <p className="mt-1 flex items-center gap-2 font-display text-2xl">
              <BadgeCheck className="h-5 w-5 text-emerald-600" />
              {comparison.easiest_projects[0]?.project_name ?? "-"}
            </p>
          </div>
          <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Needs Enablement</p>
            <p className="mt-1 flex items-center gap-2 font-display text-2xl">
              <ShieldAlert className="h-5 w-5 text-amber-600" />
              {comparison.hardest_projects[0]?.project_name ?? "-"}
            </p>
          </div>
        </div>

        <div className="grid gap-4 xl:grid-cols-2">
          <ComparisonColumn
            title="Best AI Fit"
            subtitle="Projects where the current workflow, quality, and readiness signals line up well."
            rows={comparison.easiest_projects}
          />
          <ComparisonColumn
            title="Needs Enablement"
            subtitle="Projects where effectiveness lags and extra repo or workflow support would likely help."
            rows={comparison.hardest_projects}
          />
        </div>

        <div className="flex items-start gap-2 rounded-xl border border-border/60 bg-muted/20 p-3 text-sm text-muted-foreground">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
          <p>
            Rankings use the existing project effectiveness score first, then break ties with
            friction, measurement confidence, and repository readiness.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
