import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { formatNumber } from "@/lib/utils"
import type { ProjectEnablementSummary } from "@/types/api"

interface ProjectEnablementCardProps {
  enablement: ProjectEnablementSummary
}

function renderCountPills(items: Record<string, number>, emptyLabel: string) {
  const entries = Object.entries(items).sort((a, b) => b[1] - a[1])
  if (entries.length === 0) {
    return <p className="text-sm text-muted-foreground">{emptyLabel}</p>
  }
  return (
    <div className="flex flex-wrap gap-2">
      {entries.map(([label, count]) => (
        <Badge key={label} variant="secondary" className="gap-1">
          <span className="capitalize">{label.replaceAll("_", " ")}</span>
          <span className="text-muted-foreground">{formatNumber(count)}</span>
        </Badge>
      ))}
    </div>
  )
}

function renderTopList(items: string[], emptyLabel: string) {
  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">{emptyLabel}</p>
  }
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <Badge key={item} variant="outline">
          {item}
        </Badge>
      ))}
    </div>
  )
}

export function ProjectEnablementCard({ enablement }: ProjectEnablementCardProps) {
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="text-sm font-medium">Enablement</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Linked Repositories</p>
            <p className="mt-1 font-display text-2xl">{formatNumber(enablement.linked_repository_count)}</p>
          </div>
          <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Top Tools</p>
            <p className="mt-1 font-display text-2xl">{formatNumber(enablement.top_tools.length)}</p>
          </div>
        </div>

        <section className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Agent Mix
          </h3>
          {renderCountPills(enablement.agent_type_counts, "No agent mix yet.")}
        </section>

        <section className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Session Types
          </h3>
          {renderCountPills(enablement.session_type_counts, "No session type telemetry yet.")}
        </section>

        <section className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Permission Modes
          </h3>
          {renderCountPills(enablement.permission_mode_counts, "No permission modes recorded yet.")}
        </section>

        <section className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Top Tools
          </h3>
          {renderTopList(enablement.top_tools, "No tool telemetry yet.")}
        </section>

        <section className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Top Models
          </h3>
          {renderTopList(enablement.top_models, "No model usage telemetry yet.")}
        </section>
      </CardContent>
    </Card>
  )
}
