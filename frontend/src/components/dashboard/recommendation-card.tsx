import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { Recommendation } from "@/types/api"

const severityVariant: Record<string, "default" | "warning" | "destructive" | "secondary"> = {
  critical: "destructive",
  warning: "warning",
  info: "secondary",
}

export function RecommendationCard({
  rec,
  onCreateIntervention,
}: {
  rec: Recommendation
  onCreateIntervention?: () => void
}) {
  return (
    <div className="rounded-lg border border-border p-4">
      <div className="flex items-start gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <Badge variant={severityVariant[rec.severity] ?? "secondary"}>
              {rec.severity}
            </Badge>
            <Badge variant="outline">{rec.category}</Badge>
          </div>
          <p className="mt-2 text-sm font-medium">{rec.title}</p>
          <p className="mt-1 text-sm text-muted-foreground">{rec.description}</p>
          {rec.narrative && (
            <div className="mt-3 rounded-md border border-border/70 bg-muted/30 p-3 text-sm">
              <p className="font-medium text-foreground/90">Why this helps</p>
              <p className="mt-1 text-muted-foreground">{rec.narrative.why_this_helps}</p>
              {rec.narrative.evidence_summary && (
                <p className="mt-2 text-muted-foreground">
                  <span className="font-medium text-foreground/90">Evidence:</span>{" "}
                  {rec.narrative.evidence_summary}
                </p>
              )}
              {rec.narrative.expected_impact && (
                <p className="mt-1 text-muted-foreground">
                  <span className="font-medium text-foreground/90">Likely impact:</span>{" "}
                  {rec.narrative.expected_impact}
                </p>
              )}
            </div>
          )}
          {onCreateIntervention && (
            <div className="mt-3">
              <Button variant="outline" size="sm" onClick={onCreateIntervention}>
                Create intervention
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
