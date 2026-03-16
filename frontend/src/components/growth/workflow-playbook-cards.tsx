import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatDuration, formatPercent, titleize } from "@/lib/utils"
import type { WorkflowPlaybook } from "@/types/api"

interface WorkflowPlaybookCardsProps {
  playbooks: WorkflowPlaybook[]
}

const adoptionVariant: Record<string, "default" | "secondary" | "outline"> = {
  not_used: "default",
  underused: "secondary",
  already_using: "outline",
}

export function WorkflowPlaybookCards({ playbooks }: WorkflowPlaybookCardsProps) {
  if (playbooks.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">
        No peer workflow playbooks available yet.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {playbooks.map((playbook) => (
        <Card key={playbook.playbook_id}>
          <CardHeader className="pb-3">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1">
                <CardTitle className="text-base capitalize">{playbook.title}</CardTitle>
                <p className="text-sm text-muted-foreground">{playbook.summary}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge variant={adoptionVariant[playbook.adoption_state] ?? "outline"}>
                  {titleize(playbook.adoption_state)}
                </Badge>
                <Badge variant="outline" className="capitalize">
                  {playbook.scope}
                </Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-4">
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Success</p>
                <p className="mt-1 font-display text-2xl">{formatPercent(playbook.success_rate)}</p>
              </div>
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">
                  Friction-Free
                </p>
                <p className="mt-1 font-display text-2xl">
                  {formatPercent(playbook.friction_free_rate)}
                </p>
              </div>
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Peer Proof</p>
                <p className="mt-1 font-display text-2xl">
                  {playbook.supporting_peer_count}
                  <span className="ml-1 text-sm text-muted-foreground">
                    / {playbook.supporting_session_count} sessions
                  </span>
                </p>
              </div>
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">
                  Typical Duration
                </p>
                <p className="mt-1 font-display text-2xl">
                  {playbook.avg_duration_seconds != null
                    ? formatDuration(playbook.avg_duration_seconds)
                    : "-"}
                </p>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              {playbook.steps.map((step) => (
                <Badge key={step} variant="outline" className="capitalize">
                  {titleize(step)}
                </Badge>
              ))}
            </div>

            <div className="grid gap-4 lg:grid-cols-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Recommended Tools
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {playbook.recommended_tools.length === 0 ? (
                    <span className="text-sm text-muted-foreground">No tool telemetry</span>
                  ) : (
                    playbook.recommended_tools.map((tool) => (
                      <Badge key={tool} variant="secondary">
                        {tool}
                      </Badge>
                    ))
                  )}
                </div>
              </div>

              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Watch Outs
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {playbook.caution_friction_types.length === 0 ? (
                    <span className="text-sm text-muted-foreground">No repeated frictions</span>
                  ) : (
                    playbook.caution_friction_types.map((friction) => (
                      <Badge key={friction} variant="secondary" className="capitalize">
                        {titleize(friction)}
                      </Badge>
                    ))
                  )}
                </div>
              </div>

              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Example Projects
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {playbook.example_projects.length === 0 ? (
                    <span className="text-sm text-muted-foreground">No project examples yet</span>
                  ) : (
                    playbook.example_projects.map((project) => (
                      <Badge key={project} variant="outline">
                        {project}
                      </Badge>
                    ))
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
