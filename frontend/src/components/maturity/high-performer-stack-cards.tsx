import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatLabel } from "@/lib/utils"
import type { HighPerformerStack } from "@/types/api"

interface HighPerformerStackCardsProps {
  stacks: HighPerformerStack[]
}

export function HighPerformerStackCards({ stacks }: HighPerformerStackCardsProps) {
  if (stacks.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">High-Performer Stacks</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No explicit high-performer stacks detected yet.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {stacks.map((stack) => (
        <Card key={stack.stack_id}>
          <CardHeader className="pb-3">
            <div className="space-y-1">
              <CardTitle className="text-base">{stack.label}</CardTitle>
              <p className="text-sm text-muted-foreground">
                Used by {stack.engineer_count} engineer{stack.engineer_count === 1 ? "" : "s"} across{" "}
                {stack.session_count} sessions.
              </p>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-2">
              {stack.customizations.map((item) => (
                <Badge
                  key={`${stack.stack_id}:${item.customization_type}:${item.identifier}`}
                  variant="secondary"
                >
                  {item.identifier}
                </Badge>
              ))}
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">
                  Avg Effectiveness
                </p>
                <p className="mt-1 font-display text-2xl">
                  {stack.avg_effectiveness_score != null ? stack.avg_effectiveness_score.toFixed(1) : "-"}
                </p>
              </div>
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">
                  Avg Leverage
                </p>
                <p className="mt-1 font-display text-2xl">{stack.avg_leverage_score.toFixed(1)}</p>
              </div>
            </div>

            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Provenance Mix
              </p>
              <div className="flex flex-wrap gap-2">
                {stack.customizations.map((item) => (
                  <Badge
                    key={`${stack.stack_id}:${item.identifier}:provenance`}
                    variant="outline"
                  >
                    {formatLabel(item.provenance)}
                  </Badge>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Supporting Engineers
              </p>
              <div className="flex flex-wrap gap-2">
                {stack.top_engineers.map((engineer) => (
                  <Badge key={engineer} variant="outline">
                    {engineer}
                  </Badge>
                ))}
              </div>
            </div>

            {stack.top_projects.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Example Projects
                </p>
                <div className="flex flex-wrap gap-2">
                  {stack.top_projects.map((project) => (
                    <Badge key={project} variant="outline">
                      {project}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
