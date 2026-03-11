import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatCost, formatNumber, formatPercent } from "@/lib/utils"
import type { AgentType, ProjectAgentMixSummary } from "@/types/api"

interface ProjectAgentMixCardProps {
  agentMix: ProjectAgentMixSummary
}

const AGENT_LABELS: Record<AgentType, string> = {
  claude_code: "Claude Code",
  codex_cli: "Codex CLI",
  gemini_cli: "Gemini CLI",
  cursor: "Cursor",
}

function agentLabel(agentType: AgentType): string {
  return AGENT_LABELS[agentType] ?? agentType.replaceAll("_", " ")
}

function renderBadgeList(items: string[], emptyLabel: string) {
  if (items.length === 0) {
    return <span className="text-sm text-muted-foreground">{emptyLabel}</span>
  }
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <Badge key={item} variant="secondary">
          {item}
        </Badge>
      ))}
    </div>
  )
}

export function ProjectAgentMixCard({ agentMix }: ProjectAgentMixCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Agent Mix Comparison</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Leading Agent</p>
            <p className="mt-1 font-display text-2xl">
              {agentMix.dominant_agent_type ? agentLabel(agentMix.dominant_agent_type) : "-"}
            </p>
          </div>
          <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Agents in Mix</p>
            <p className="mt-1 font-display text-2xl">{formatNumber(agentMix.compared_agents)}</p>
          </div>
          <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Sessions Compared</p>
            <p className="mt-1 font-display text-2xl">{formatNumber(agentMix.total_sessions)}</p>
          </div>
        </div>

        {agentMix.entries.length === 0 ? (
          <p className="text-sm text-muted-foreground">No multi-agent activity recorded yet.</p>
        ) : (
          <div className="space-y-3">
            {agentMix.entries.map((entry) => (
              <div
                key={entry.agent_type}
                className="rounded-xl border border-border/60 bg-background p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="space-y-1">
                    <p className="font-medium">{agentLabel(entry.agent_type)}</p>
                    <p className="text-sm text-muted-foreground">
                      {formatNumber(entry.session_count)} sessions
                      {" • "}
                      {formatNumber(entry.unique_engineers)} engineers
                    </p>
                  </div>
                  <Badge variant="outline">{formatPercent(entry.share_of_sessions)} share</Badge>
                </div>

                <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                  <div className="rounded-lg border border-border/50 bg-muted/20 p-3">
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">Success</p>
                    <p className="mt-1 font-display text-xl">{formatPercent(entry.success_rate)}</p>
                  </div>
                  <div className="rounded-lg border border-border/50 bg-muted/20 p-3">
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">Friction</p>
                    <p className="mt-1 font-display text-xl">{formatPercent(entry.friction_rate)}</p>
                  </div>
                  <div className="rounded-lg border border-border/50 bg-muted/20 p-3">
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">Avg Health</p>
                    <p className="mt-1 font-display text-xl">
                      {entry.avg_health_score != null ? entry.avg_health_score.toFixed(1) : "-"}
                    </p>
                  </div>
                  <div className="rounded-lg border border-border/50 bg-muted/20 p-3">
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">Avg Cost</p>
                    <p className="mt-1 font-display text-xl">
                      {entry.avg_cost_per_session != null ? formatCost(entry.avg_cost_per_session) : "-"}
                    </p>
                  </div>
                </div>

                <div className="mt-3 grid gap-3 lg:grid-cols-2">
                  <div className="space-y-2">
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Top Tools
                    </p>
                    {renderBadgeList(entry.top_tools, "No tool telemetry")}
                  </div>
                  <div className="space-y-2">
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Top Models
                    </p>
                    {renderBadgeList(entry.top_models, "No model telemetry")}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
