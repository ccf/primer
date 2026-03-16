import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatPercent, titleize } from "@/lib/utils"
import type { RootCauseCluster } from "@/types/api"

interface RootCauseClusterListProps {
  data: RootCauseCluster[]
}

export function RootCauseClusterList({ data }: RootCauseClusterListProps) {
  if (data.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Root-Cause Clusters</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {data.map((cluster) => (
          <div
            key={cluster.cluster_id}
            className="rounded-xl border border-border/60 bg-background p-4"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1">
                <p className="font-medium">{cluster.title}</p>
                <p className="text-sm text-muted-foreground">
                  {cluster.session_count} sessions • {cluster.occurrence_count} occurrences
                </p>
              </div>
              <div className="text-right text-sm text-muted-foreground">
                <p>Success {formatPercent(cluster.success_rate)}</p>
                <p>
                  Avg impact{" "}
                  {cluster.avg_impact_score != null
                    ? `${(cluster.avg_impact_score * 100).toFixed(1)}pp`
                    : "--"}
                </p>
              </div>
            </div>

            <div className="mt-3 grid gap-3 lg:grid-cols-3">
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Friction Types
                </p>
                <div className="flex flex-wrap gap-2">
                  {cluster.top_friction_types.map((frictionType) => (
                    <Badge key={frictionType} variant="secondary" className="capitalize">
                      {titleize(frictionType)}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Tool Traces
                </p>
                <div className="flex flex-wrap gap-2">
                  {cluster.common_tools.length === 0 ? (
                    <span className="text-sm text-muted-foreground">No tool evidence</span>
                  ) : (
                    cluster.common_tools.map((tool) => (
                      <Badge key={tool} variant="outline">
                        {tool}
                      </Badge>
                    ))
                  )}
                </div>
              </div>

              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Transcript Cues
                </p>
                <div className="flex flex-wrap gap-2">
                  {cluster.transcript_cues.length === 0 ? (
                    <span className="text-sm text-muted-foreground">No repeated cues</span>
                  ) : (
                    cluster.transcript_cues.map((cue) => (
                      <Badge key={cue} variant="outline">
                        {cue}
                      </Badge>
                    ))
                  )}
                </div>
              </div>
            </div>

            {cluster.sample_details.length > 0 && (
              <div className="mt-3 space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Sample Evidence
                </p>
                {cluster.sample_details.map((detail) => (
                  <p
                    key={detail}
                    className="rounded-lg bg-muted/40 px-3 py-2 text-sm text-muted-foreground"
                  >
                    {detail}
                  </p>
                ))}
              </div>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
