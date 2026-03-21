import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatCost, formatLabel, formatPercent } from "@/lib/utils"
import type { ModelRecommendation } from "@/types/api"

interface ModelRecommendationListProps {
  recommendations: ModelRecommendation[]
}

const priorityVariant: Record<string, "warning" | "destructive" | "secondary"> = {
  high: "warning",
  medium: "secondary",
  low: "secondary",
}

export function ModelRecommendationList({ recommendations }: ModelRecommendationListProps) {
  if (recommendations.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Model Selection Coach</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No model recommendations available yet.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {recommendations.map((recommendation) => (
        <Card
          key={`${recommendation.workflow_archetype}:${recommendation.current_model}:${recommendation.recommended_model}`}
        >
          <CardHeader className="pb-3">
            <div className="flex items-start justify-between gap-3">
              <div className="space-y-1">
                <CardTitle className="text-base">{recommendation.title}</CardTitle>
                <p className="text-sm text-muted-foreground">{recommendation.description}</p>
              </div>
              <Badge variant={priorityVariant[recommendation.priority] ?? "secondary"}>
                {recommendation.priority}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline">{formatLabel(recommendation.recommendation_type)}</Badge>
              {recommendation.workflow_archetype && (
                <Badge variant="outline">{formatLabel(recommendation.workflow_archetype)}</Badge>
              )}
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <p className="text-xs uppercase tracking-wide text-muted-foreground">
                  Current Model
                </p>
                <p className="mt-1 font-medium">{recommendation.current_model}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-muted-foreground">
                  Recommended Model
                </p>
                <p className="mt-1 font-medium">{recommendation.recommended_model}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-muted-foreground">
                  Success
                </p>
                <p className="mt-1 text-sm">
                  {formatPercent(recommendation.current_success_rate)}
                  {" -> "}
                  {formatPercent(recommendation.recommended_success_rate)}
                </p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-muted-foreground">
                  Avg Cost
                </p>
                <p className="mt-1 text-sm">
                  {recommendation.current_avg_cost != null
                    ? formatCost(recommendation.current_avg_cost)
                    : "-"}
                  {" -> "}
                  {recommendation.recommended_avg_cost != null
                    ? formatCost(recommendation.recommended_avg_cost)
                    : "-"}
                </p>
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              Supported by {recommendation.supporting_session_count} sessions from{" "}
              {recommendation.supporting_engineer_count} engineers.
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
