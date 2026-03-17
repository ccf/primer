import { Link } from "react-router-dom"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatCost, formatDuration, formatLabel } from "@/lib/utils"
import type { ToolRecommendation } from "@/types/api"

interface ToolRecommendationListProps {
  recommendations: ToolRecommendation[]
}

export function ToolRecommendationList({ recommendations }: ToolRecommendationListProps) {
  if (recommendations.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">
        No tool recommendations available yet.
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {recommendations.map((recommendation) => (
        <Card key={recommendation.tool_name}>
          <CardHeader className="pb-3">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1">
                <CardTitle className="text-base">{recommendation.title}</CardTitle>
                <p className="text-sm text-muted-foreground">{recommendation.description}</p>
              </div>
              <Badge variant={recommendation.priority === "high" ? "warning" : "outline"}>
                {recommendation.priority}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Tool</p>
                <p className="mt-1 font-display text-2xl">{recommendation.tool_name}</p>
              </div>
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">
                  Exemplars
                </p>
                <p className="mt-1 font-display text-2xl">
                  {recommendation.supporting_exemplar_count}
                </p>
              </div>
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">
                  Project Matches
                </p>
                <p className="mt-1 font-display text-2xl">
                  {recommendation.project_context_match_count}
                </p>
              </div>
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">
                  Skill Areas
                </p>
                <p className="mt-1 font-display text-2xl">
                  {recommendation.related_skill_areas.length}
                </p>
              </div>
            </div>

            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Relevant Work
              </p>
              <div className="flex flex-wrap gap-2">
                {recommendation.related_skill_areas.map((area) => (
                  <Badge key={area} variant="secondary">
                    {formatLabel(area)}
                  </Badge>
                ))}
                {recommendation.matching_projects.map((project) => (
                  <Badge key={project} variant="outline">
                    {project}
                  </Badge>
                ))}
              </div>
            </div>

            {recommendation.exemplar && (
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Best Exemplar
                </p>
                <Link
                  to={`/sessions/${recommendation.exemplar.session_id}`}
                  className="block rounded-xl border border-border/60 bg-background p-4 hover:bg-muted/20"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-1">
                      <p className="font-medium">{recommendation.exemplar.title}</p>
                      <p className="text-sm text-muted-foreground">
                        {recommendation.exemplar.engineer_name}
                        {recommendation.exemplar.project_name
                          ? ` • ${recommendation.exemplar.project_name}`
                          : ""}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {recommendation.exemplar.relevance_reason}
                      </p>
                    </div>
                    <div className="text-right text-sm text-muted-foreground">
                      <p>{formatDuration(recommendation.exemplar.duration_seconds)}</p>
                      {recommendation.exemplar.estimated_cost != null && (
                        <p>{formatCost(recommendation.exemplar.estimated_cost)}</p>
                      )}
                    </div>
                  </div>
                </Link>
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
