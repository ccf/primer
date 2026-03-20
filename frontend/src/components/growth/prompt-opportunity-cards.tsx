import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatCost, formatLabel, formatPercent } from "@/lib/utils"
import type { PromptReusePattern } from "@/types/api"

interface PromptOpportunityCardsProps {
  patterns: PromptReusePattern[]
}

export function PromptOpportunityCards({ patterns }: PromptOpportunityCardsProps) {
  if (patterns.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Underused High-Value Prompts</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No high-value prompt opportunities identified yet.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-3">
      <div className="space-y-1">
        <h3 className="text-sm font-medium">Underused High-Value Prompts</h3>
        <p className="text-sm text-muted-foreground">
          Prompt patterns that work well but have not spread broadly yet.
        </p>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        {patterns.map((pattern) => (
          <Card key={pattern.prompt_pattern_id}>
            <CardHeader className="pb-3">
              <div className="space-y-1">
                <CardTitle className="text-base">{pattern.prompt_preview}</CardTitle>
                <p className="font-mono text-[10px] text-muted-foreground">
                  {pattern.normalized_prompt}
                </p>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid gap-3 sm:grid-cols-3">
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">
                    Adoption
                  </p>
                  <p className="mt-1 text-lg font-semibold">{formatPercent(pattern.adoption_rate)}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">
                    Success
                  </p>
                  <p className="mt-1 text-lg font-semibold">{formatPercent(pattern.success_rate)}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">
                    Cost / Success
                  </p>
                  <p className="mt-1 text-lg font-semibold">
                    {pattern.cost_per_successful_outcome != null
                      ? formatCost(pattern.cost_per_successful_outcome)
                      : "-"}
                  </p>
                </div>
              </div>

              <div className="space-y-2">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">
                  Workflow Fit
                </p>
                <div className="flex flex-wrap gap-2">
                  {pattern.workflow_archetypes.length === 0 ? (
                    <span className="text-xs text-muted-foreground">No workflow signal yet</span>
                  ) : (
                    pattern.workflow_archetypes.map((workflow) => (
                      <Badge key={`${pattern.prompt_pattern_id}:${workflow}`} variant="outline">
                        {formatLabel(workflow)}
                      </Badge>
                    ))
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
