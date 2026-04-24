import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { formatLabel, formatMetric, formatPercent } from "@/lib/utils"
import type { HarnessConfigurationFingerprint } from "@/types/api"

interface HarnessFingerprintTableProps {
  rows: HarnessConfigurationFingerprint[]
}

export function HarnessFingerprintTable({ rows }: HarnessFingerprintTableProps) {
  if (rows.length === 0) {
    return (
      <Card>
        <CardHeader>
          <h3 className="text-sm font-medium">Harness Configuration Fingerprints</h3>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No harness configuration fingerprints available yet.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <h3 className="text-sm font-medium">Harness Configuration Fingerprints</h3>
        <p className="text-sm text-muted-foreground">
          Group sessions by the actual harness shape: agent, permission boundary, tools, context,
          and customizations.
        </p>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="pb-2 font-medium">Fingerprint</th>
                <th className="pb-2 text-right font-medium">Sessions</th>
                <th className="pb-2 text-right font-medium">Success</th>
                <th className="pb-2 text-right font-medium">Leverage</th>
                <th className="pb-2 text-right font-medium">Shape</th>
                <th className="pb-2 font-medium">Top Signals</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.fingerprint_id} className="border-b border-border/40">
                  <td className="py-2">
                    <div className="space-y-1">
                      <p className="font-medium">{row.label}</p>
                      <p className="font-mono text-xs text-muted-foreground">
                        {row.fingerprint_id}
                      </p>
                      <div className="flex flex-wrap gap-2">
                        <Badge variant="outline">{formatLabel(row.agent_type)}</Badge>
                        <Badge variant="secondary">{formatLabel(row.permission_mode)}</Badge>
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
                      <p>{formatPercent(row.success_rate)}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatPercent(row.compound_reliability_rate)} 10-step
                      </p>
                    </div>
                  </td>
                  <td className="py-2 text-right">
                    <div>
                      <p>{formatMetric(row.avg_leverage_score)}</p>
                      <p className="text-xs text-muted-foreground">avg score</p>
                    </div>
                  </td>
                  <td className="py-2 text-right">
                    <div>
                      <p>{row.tool_count} tools</p>
                      <p className="text-xs text-muted-foreground">
                        {row.customization_count} custom, {row.context_signal_count} context
                      </p>
                    </div>
                  </td>
                  <td className="py-2">
                    <div className="flex max-w-xl flex-wrap gap-2">
                      {row.top_tools.map((tool) => (
                        <Badge key={`${row.fingerprint_id}:tool:${tool}`} variant="outline">
                          {formatLabel(tool)}
                        </Badge>
                      ))}
                      {row.top_customizations.map((customization) => (
                        <Badge
                          key={`${row.fingerprint_id}:customization:${customization}`}
                          variant="secondary"
                        >
                          {customization}
                        </Badge>
                      ))}
                      {row.signals.map((signal) => (
                        <Badge key={`${row.fingerprint_id}:signal:${signal}`} variant="outline">
                          {formatLabel(signal)}
                        </Badge>
                      ))}
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
