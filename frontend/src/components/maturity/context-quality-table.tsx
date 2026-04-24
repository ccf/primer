import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { formatMetric, formatPercent, formatTokens } from "@/lib/utils"
import type { ContextQualityEntry } from "@/types/api"

interface ContextQualityTableProps {
  rows: ContextQualityEntry[]
}

function formatCoverage(value: number): string {
  return `${value.toFixed(0)}%`
}

export function ContextQualityTable({ rows }: ContextQualityTableProps) {
  if (rows.length === 0) {
    return (
      <Card>
        <CardHeader>
          <h3 className="text-sm font-medium">Context Quality</h3>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No context quality signals available yet.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <h3 className="text-sm font-medium">Context Quality</h3>
        <p className="text-sm text-muted-foreground">
          Scores project context by guidance coverage, freshness, token efficiency, and telemetry
          sensor coverage.
        </p>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="pb-2 font-medium">Repository</th>
                <th className="pb-2 text-right font-medium">Score</th>
                <th className="pb-2 text-right font-medium">Guides</th>
                <th className="pb-2 text-right font-medium">Tokens</th>
                <th className="pb-2 text-right font-medium">Sensors</th>
                <th className="pb-2 font-medium">Top Gaps</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.repository} className="border-b border-border/40">
                  <td className="py-2">
                    <div className="space-y-1">
                      <p className="font-mono text-xs">{row.repository}</p>
                      <p className="text-xs text-muted-foreground">{row.session_count} sessions</p>
                    </div>
                  </td>
                  <td className="py-2 text-right">
                    <div>
                      <p className="font-medium">{formatMetric(row.context_quality_score)}</p>
                      <p className="text-xs text-muted-foreground">overall</p>
                    </div>
                  </td>
                  <td className="py-2 text-right">
                    <div>
                      <p>{formatMetric(row.guide_coverage_score)}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatMetric(row.guide_freshness_score, 0)} fresh
                      </p>
                    </div>
                  </td>
                  <td className="py-2 text-right">
                    <div>
                      <p>{formatMetric(row.token_efficiency_score)}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatPercent(row.cache_hit_rate)} cache,{" "}
                        {row.avg_input_tokens == null
                          ? "-"
                          : formatTokens(row.avg_input_tokens)}{" "}
                        avg input
                      </p>
                    </div>
                  </td>
                  <td className="py-2 text-right">
                    <div>
                      <p>{formatMetric(row.sensor_coverage_score)}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatCoverage(row.context_usage_coverage_pct)} context /{" "}
                        {formatCoverage(row.model_coverage_pct)} models
                      </p>
                    </div>
                  </td>
                  <td className="py-2">
                    <div className="flex flex-wrap gap-2">
                      {row.top_gaps.length === 0 ? (
                        <span className="text-xs text-muted-foreground">No major gaps</span>
                      ) : (
                        row.top_gaps.map((gap) => (
                          <Badge key={`${row.repository}:${gap}`} variant="outline">
                            {gap}
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
