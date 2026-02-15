import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { PatternSharingResponse } from "@/types/api"

interface PatternSummaryProps {
  data: PatternSharingResponse
}

export function PatternSummary({ data }: PatternSummaryProps) {
  const typeCounts: Record<string, number> = {}
  for (const p of data.patterns) {
    typeCounts[p.cluster_type] = (typeCounts[p.cluster_type] ?? 0) + 1
  }

  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">Patterns Found</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{data.total_clusters_found}</div>
          <p className="text-xs text-muted-foreground">{data.sessions_analyzed} sessions analyzed</p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">By Type</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-1">
            {Object.entries(typeCounts).map(([type, count]) => (
              <div key={type} className="flex justify-between text-sm">
                <span className="capitalize text-muted-foreground">{type.replace(/_/g, " ")}</span>
                <span className="font-medium">{count}</span>
              </div>
            ))}
            {Object.keys(typeCounts).length === 0 && (
              <span className="text-sm text-muted-foreground">No clusters yet</span>
            )}
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">Avg Engineers/Pattern</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {data.patterns.length > 0
              ? (data.patterns.reduce((s, p) => s + p.engineer_count, 0) / data.patterns.length).toFixed(1)
              : "0"}
          </div>
          <p className="text-xs text-muted-foreground">collaboration density</p>
        </CardContent>
      </Card>
    </div>
  )
}
