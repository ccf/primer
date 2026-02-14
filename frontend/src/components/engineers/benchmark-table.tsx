import { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatCost, formatTokens, formatDuration } from "@/lib/utils"
import { BenchmarkRadar } from "./benchmark-radar"
import type { EngineerBenchmark, BenchmarkContext } from "@/types/api"

interface BenchmarkTableProps {
  engineers: EngineerBenchmark[]
  benchmark: BenchmarkContext
}

function PercentileBadge({ value }: { value: number }) {
  if (value >= 90) return <Badge variant="success">Top 10%</Badge>
  if (value >= 75) return <Badge className="bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">Top 25%</Badge>
  if (value >= 50) return <Badge variant="secondary">Top 50%</Badge>
  return <Badge variant="outline">Bottom 50%</Badge>
}

function DeltaIndicator({ value }: { value: number | undefined }) {
  if (value === undefined) return <span className="text-muted-foreground">-</span>
  const positive = value > 0
  return (
    <span className={positive ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}>
      {positive ? "+" : ""}{value.toFixed(1)}%
    </span>
  )
}

export function BenchmarkTable({ engineers, benchmark }: BenchmarkTableProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Engineer Benchmarks</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/50">
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Engineer</th>
                <th className="px-4 py-3 text-right font-medium text-muted-foreground">Sessions</th>
                <th className="px-4 py-3 text-right font-medium text-muted-foreground">vs Avg</th>
                <th className="px-4 py-3 text-right font-medium text-muted-foreground">Cost</th>
                <th className="px-4 py-3 text-right font-medium text-muted-foreground">Success</th>
                <th className="px-4 py-3 text-right font-medium text-muted-foreground">Avg Duration</th>
                <th className="px-4 py-3 text-center font-medium text-muted-foreground">Rank</th>
              </tr>
            </thead>
            <tbody>
              {engineers.map((eng) => (
                <>
                  <tr
                    key={eng.engineer_id}
                    className="cursor-pointer border-b border-border last:border-0 hover:bg-muted/30"
                    onClick={() => setExpandedId(expandedId === eng.engineer_id ? null : eng.engineer_id)}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {eng.avatar_url ? (
                          <img src={eng.avatar_url} alt={eng.display_name ?? eng.name} className="h-7 w-7 rounded-full" />
                        ) : (
                          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-muted text-xs font-medium">
                            {(eng.display_name ?? eng.name).charAt(0).toUpperCase()}
                          </div>
                        )}
                        <span className="font-medium">{eng.display_name ?? eng.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">{eng.total_sessions}</td>
                    <td className="px-4 py-3 text-right">
                      <DeltaIndicator value={eng.vs_team_avg.sessions} />
                    </td>
                    <td className="px-4 py-3 text-right">{formatCost(eng.estimated_cost)}</td>
                    <td className="px-4 py-3 text-right">
                      {eng.success_rate != null ? `${(eng.success_rate * 100).toFixed(0)}%` : "-"}
                    </td>
                    <td className="px-4 py-3 text-right">{formatDuration(eng.avg_duration)}</td>
                    <td className="px-4 py-3 text-center">
                      <PercentileBadge value={eng.percentile_sessions} />
                    </td>
                  </tr>
                  {expandedId === eng.engineer_id && (
                    <tr key={`${eng.engineer_id}-expanded`}>
                      <td colSpan={7} className="bg-muted/20 px-4 py-4">
                        <div className="mx-auto max-w-md">
                          <BenchmarkRadar engineer={eng} benchmark={benchmark} />
                        </div>
                        <div className="mt-3 flex justify-center gap-6 text-xs text-muted-foreground">
                          <span>Tokens: {formatTokens(eng.total_tokens)} <DeltaIndicator value={eng.vs_team_avg.tokens} /></span>
                          <span>Cost: {formatCost(eng.estimated_cost)} <DeltaIndicator value={eng.vs_team_avg.cost} /></span>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}
