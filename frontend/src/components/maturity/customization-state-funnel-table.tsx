import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { formatLabel, formatPercent } from "@/lib/utils"
import type { CustomizationStateFunnel } from "@/types/api"

interface CustomizationStateFunnelTableProps {
  rows: CustomizationStateFunnel[]
}

export function CustomizationStateFunnelTable({ rows }: CustomizationStateFunnelTableProps) {
  if (rows.length === 0) {
    return (
      <Card>
        <CardHeader>
          <h3 className="text-sm font-medium">Customization State Funnel</h3>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No customization state coverage available yet.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <h3 className="text-sm font-medium">Customization State Funnel</h3>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="pb-2 font-medium">Identifier</th>
                <th className="pb-2 font-medium">Details</th>
                <th className="pb-2 text-right font-medium">Available</th>
                <th className="pb-2 text-right font-medium">Enabled</th>
                <th className="pb-2 text-right font-medium">Invoked</th>
                <th className="pb-2 text-right font-medium">Activation</th>
                <th className="pb-2 text-right font-medium">Usage</th>
                <th className="pb-2 font-medium">State Gaps</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={`${row.customization_type}:${row.identifier}:${row.provenance}:${row.source_classification}`}
                  className="border-b border-border/40"
                >
                  <td className="py-2 font-mono text-xs">{row.identifier}</td>
                  <td className="py-2">
                    <div className="flex flex-wrap gap-2">
                      <Badge variant="outline">{formatLabel(row.customization_type)}</Badge>
                      <Badge variant="secondary">{formatLabel(row.provenance)}</Badge>
                      <Badge variant="outline">{formatLabel(row.source_classification)}</Badge>
                    </div>
                  </td>
                  <td className="py-2 text-right">
                    <div>
                      <p>{row.available_engineer_count}</p>
                      <p className="text-xs text-muted-foreground">
                        {row.available_session_count} sessions
                      </p>
                    </div>
                  </td>
                  <td className="py-2 text-right">
                    <div>
                      <p>{row.enabled_engineer_count}</p>
                      <p className="text-xs text-muted-foreground">
                        {row.enabled_session_count} sessions
                      </p>
                    </div>
                  </td>
                  <td className="py-2 text-right">
                    <div>
                      <p>{row.invoked_engineer_count}</p>
                      <p className="text-xs text-muted-foreground">
                        {row.invoked_session_count} sessions
                      </p>
                    </div>
                  </td>
                  <td className="py-2 text-right">{formatPercent(row.activation_rate)}</td>
                  <td className="py-2 text-right">{formatPercent(row.usage_rate)}</td>
                  <td className="py-2">
                    <div className="flex flex-wrap gap-2">
                      {row.available_not_enabled_engineer_count > 0 && (
                        <Badge variant="outline">
                          {row.available_not_enabled_engineer_count} available not enabled
                        </Badge>
                      )}
                      {row.enabled_not_invoked_engineer_count > 0 && (
                        <Badge variant="outline">
                          {row.enabled_not_invoked_engineer_count} enabled not invoked
                        </Badge>
                      )}
                      {row.available_not_enabled_engineer_count === 0 &&
                        row.enabled_not_invoked_engineer_count === 0 && (
                          <span className="text-xs text-muted-foreground">No gaps detected</span>
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
