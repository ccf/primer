import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { formatCost, formatLabel, formatPercent } from "@/lib/utils"
import type { AgentTeamModeSummary } from "@/types/api"

interface AgentTeamModeTableProps {
  rows: AgentTeamModeSummary[]
}

export function AgentTeamModeTable({ rows }: AgentTeamModeTableProps) {
  if (rows.length === 0) {
    return (
      <Card>
        <CardHeader>
          <h3 className="text-sm font-medium">Agent Team Modes</h3>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No agent team coordination patterns detected yet.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <h3 className="text-sm font-medium">Agent Team Modes</h3>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="pb-2 font-medium">Mode</th>
                <th className="pb-2 text-right font-medium">Sessions</th>
                <th className="pb-2 text-right font-medium">Engineers</th>
                <th className="pb-2 text-right font-medium">Success</th>
                <th className="pb-2 text-right font-medium">Avg Cost</th>
                <th className="pb-2 text-right font-medium">Avg Delegations</th>
                <th className="pb-2 font-medium">Top Targets</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.coordination_mode} className="border-b border-border/40">
                  <td className="py-2">
                    <div className="space-y-1">
                      <Badge variant="outline">{formatLabel(row.coordination_mode)}</Badge>
                      <p className="text-xs text-muted-foreground">
                        {formatPercent(row.session_share)} of sessions
                      </p>
                    </div>
                  </td>
                  <td className="py-2 text-right">{row.session_count}</td>
                  <td className="py-2 text-right">{row.engineer_count}</td>
                  <td className="py-2 text-right">{formatPercent(row.success_rate)}</td>
                  <td className="py-2 text-right">
                    {row.avg_cost_per_session != null ? formatCost(row.avg_cost_per_session) : "-"}
                  </td>
                  <td className="py-2 text-right">{row.avg_delegation_edges.toFixed(2)}</td>
                  <td className="py-2">
                    <div className="flex flex-wrap gap-2">
                      {row.top_targets.length === 0 ? (
                        <span className="text-xs text-muted-foreground">No delegated targets</span>
                      ) : (
                        row.top_targets.map((target) => (
                          <Badge key={`${row.coordination_mode}:${target}`} variant="outline">
                            {target}
                          </Badge>
                        ))
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}
