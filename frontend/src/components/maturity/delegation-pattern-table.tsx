import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { formatLabel, formatPercent } from "@/lib/utils"
import type { DelegationPatternSummary } from "@/types/api"

interface DelegationPatternTableProps {
  rows: DelegationPatternSummary[]
}

export function DelegationPatternTable({ rows }: DelegationPatternTableProps) {
  if (rows.length === 0) {
    return (
      <Card>
        <CardHeader>
          <h3 className="text-sm font-medium">Delegation Patterns</h3>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No delegation patterns detected yet.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <h3 className="text-sm font-medium">Delegation Patterns</h3>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="pb-2 font-medium">Target</th>
                <th className="pb-2 font-medium">Edge Type</th>
                <th className="pb-2 text-right font-medium">Calls</th>
                <th className="pb-2 text-right font-medium">Sessions</th>
                <th className="pb-2 text-right font-medium">Engineers</th>
                <th className="pb-2 text-right font-medium">Success</th>
                <th className="pb-2 font-medium">Top Workflows</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={`${row.edge_type}:${row.target_node}`}
                  className="border-b border-border/40"
                >
                  <td className="py-2 font-mono text-xs">{row.target_node}</td>
                  <td className="py-2">
                    <Badge variant="outline">{formatLabel(row.edge_type)}</Badge>
                  </td>
                  <td className="py-2 text-right">{row.total_calls}</td>
                  <td className="py-2 text-right">{row.session_count}</td>
                  <td className="py-2 text-right">{row.engineer_count}</td>
                  <td className="py-2 text-right">{formatPercent(row.success_rate)}</td>
                  <td className="py-2">
                    <div className="flex flex-wrap gap-2">
                      {row.top_workflow_archetypes.length === 0 ? (
                        <span className="text-xs text-muted-foreground">No workflow signal yet</span>
                      ) : (
                        row.top_workflow_archetypes.map((workflow) => (
                          <Badge key={`${row.target_node}:${workflow}`} variant="outline">
                            {formatLabel(workflow)}
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
