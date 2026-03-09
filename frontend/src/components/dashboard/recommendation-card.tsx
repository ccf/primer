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
