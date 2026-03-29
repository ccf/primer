import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { RecommendationNarrativeBlock } from "@/components/shared/recommendation-narrative-block"
import type { NextStepPlanResponse } from "@/types/api"

interface NextStepPlanSectionProps {
  plan: NextStepPlanResponse
}

const priorityVariant: Record<string, "default" | "secondary" | "outline"> = {
  high: "default",
  medium: "secondary",
  low: "outline",
}

export function NextStepPlanSection({ plan }: NextStepPlanSectionProps) {
  if (plan.actions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Auto-generated next steps</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{plan.summary}</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium">Auto-generated next steps</CardTitle>
        <p className="text-sm text-muted-foreground">{plan.summary}</p>
      </CardHeader>
      <CardContent className="space-y-4">
        {plan.actions.map((action) => (
          <div
            key={action.action_id}
            className="rounded-2xl border border-border/70 bg-card/70 p-4"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={priorityVariant[action.priority] ?? "outline"}>
                    {action.priority}
                  </Badge>
                  <Badge variant="outline">{action.source_type.replace("_", " ")}</Badge>
                  {action.project_name && <Badge variant="outline">{action.project_name}</Badge>}
                </div>
                <p className="text-base font-semibold">{action.title}</p>
                <p className="text-sm text-muted-foreground">{action.description}</p>
                {action.narrative && (
                  <RecommendationNarrativeBlock
                    narrative={action.narrative}
                    className="rounded-xl bg-muted/20"
                  />
                )}
              </div>
              {action.source_title && (
                <p className="text-xs text-muted-foreground">{action.source_title}</p>
              )}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
