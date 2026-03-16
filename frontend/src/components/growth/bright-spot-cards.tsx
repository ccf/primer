import { Link } from "react-router-dom"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { formatDuration, formatLabel, formatPercent } from "@/lib/utils"
import type { BrightSpot } from "@/types/api"

interface BrightSpotCardsProps {
  spots: BrightSpot[]
}

export function BrightSpotCards({ spots }: BrightSpotCardsProps) {
  if (spots.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">
        No bright spots identified yet.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {spots.map((spot) => (
        <Card key={spot.bright_spot_id}>
          <CardHeader className="pb-3">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1">
                <CardTitle className="text-base">{spot.title}</CardTitle>
                <p className="text-sm text-muted-foreground">{spot.summary}</p>
              </div>
              <Badge variant="success" className="capitalize">
                {formatLabel(spot.cluster_type)}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-4">
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Success</p>
                <p className="mt-1 font-display text-2xl">{formatPercent(spot.success_rate)}</p>
              </div>
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Sessions</p>
                <p className="mt-1 font-display text-2xl">{spot.session_count}</p>
              </div>
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Engineers</p>
                <p className="mt-1 font-display text-2xl">{spot.engineer_count}</p>
              </div>
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">
                  Avg Duration
                </p>
                <p className="mt-1 font-display text-2xl">{formatDuration(spot.avg_duration)}</p>
              </div>
            </div>

            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Exemplar Session
              </p>
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border/60 bg-background p-4">
                <div className="space-y-1">
                  <p className="font-medium">{spot.exemplar_engineer_name}</p>
                  <p className="text-sm text-muted-foreground">
                    {spot.cluster_label}
                    {" • "}
                    {formatDuration(spot.exemplar_duration_seconds)}
                  </p>
                </div>
                <Link
                  to={`/sessions/${spot.exemplar_session_id}`}
                  className="text-sm font-medium text-primary hover:underline"
                >
                  View session
                </Link>
              </div>
            </div>

            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Exemplar Tools
              </p>
              <div className="flex flex-wrap gap-2">
                {spot.exemplar_tools.length === 0 ? (
                  <span className="text-sm text-muted-foreground">No tool telemetry</span>
                ) : (
                  spot.exemplar_tools.map((tool) => (
                    <Badge key={tool} variant="secondary">
                      {tool}
                    </Badge>
                  ))
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
