import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { formatLabel, formatPercent } from "@/lib/utils"
import type { ToolchainReliabilityEntry } from "@/types/api"

interface ToolchainReliabilityTableProps {
  rows: ToolchainReliabilityEntry[]
}

export function ToolchainReliabilityTable({ rows }: ToolchainReliabilityTableProps) {
  if (rows.length === 0) {
    return (
      <Card>
        <CardHeader>
          <h3 className="text-sm font-medium">Toolchain Reliability</h3>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No toolchain reliability signals available yet.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <h3 className="text-sm font-medium">Toolchain Reliability</h3>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="pb-2 font-medium">Surface</th>
                <th className="pb-2 text-right font-medium">Sessions</th>
                <th className="pb-2 text-right font-medium">Friction</th>
                <th className="pb-2 text-right font-medium">Failures</th>
                <th className="pb-2 text-right font-medium">Recovery</th>
                <th className="pb-2 text-right font-medium">Success</th>
                <th className="pb-2 font-medium">Top Frictions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={`${row.surface_type}:${row.identifier}:${row.provenance ?? "none"}:${row.source_classification ?? "none"}`}
                  className="border-b border-border/40"
                >
                  <td className="py-2">
                    <div className="space-y-1">
                      <p className="font-mono text-xs">{row.identifier}</p>
                      <div className="flex flex-wrap gap-2">
                        <Badge variant="outline">{formatLabel(row.surface_type)}</Badge>
                        {row.provenance && (
                          <Badge variant="secondary">{formatLabel(row.provenance)}</Badge>
                        )}
                        {row.source_classification && (
                          <Badge variant="outline">{formatLabel(row.source_classification)}</Badge>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="py-2 text-right">
                    <div>
                      <p>{row.session_count}</p>
                      <p className="text-xs text-muted-foreground">
                        {row.engineer_count} engineers
                      </p>
                    </div>
                  </td>
                  <td className="py-2 text-right">
                    <div>
                      <p>{formatPercent(row.friction_session_rate)}</p>
                      <p className="text-xs text-muted-foreground">
                        {row.friction_session_count} sessions
                      </p>
                    </div>
                  </td>
                  <td className="py-2 text-right">
                    <div>
                      <p>{formatPercent(row.failure_session_rate)}</p>
                      <p className="text-xs text-muted-foreground">
                        {row.failure_session_count} sessions
                      </p>
                    </div>
                  </td>
                  <td className="py-2 text-right">
                    <div>
                      <p>{formatPercent(row.recovery_rate)}</p>
                      <p className="text-xs text-muted-foreground">
                        {row.avg_recovery_steps != null
                          ? `${row.avg_recovery_steps.toFixed(1)} steps`
                          : "No recoveries"}
                      </p>
                    </div>
                  </td>
                  <td className="py-2 text-right">
                    <div>
                      <p>{formatPercent(row.success_rate)}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatPercent(row.abandonment_rate)} abandoned
                      </p>
                    </div>
                  </td>
                  <td className="py-2">
                    <div className="flex flex-wrap gap-2">
                      {row.top_friction_types.length === 0 ? (
                        <span className="text-xs text-muted-foreground">No recurring friction</span>
                      ) : (
                        row.top_friction_types.map((item) => (
                          <Badge key={`${row.identifier}:${item}`} variant="outline">
                            {formatLabel(item)}
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
