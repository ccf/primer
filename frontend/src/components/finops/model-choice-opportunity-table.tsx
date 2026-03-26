import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatCost, formatLabel, formatPercent } from "@/lib/utils"
import type { ModelChoiceOpportunity } from "@/types/api"

interface ModelChoiceOpportunityTableProps {
  opportunities: ModelChoiceOpportunity[]
  totalSavingsMonthly: number
}

const confidenceVariant: Record<string, "default" | "secondary" | "outline"> = {
  high: "default",
  medium: "secondary",
  low: "outline",
}

export function ModelChoiceOpportunityTable({
  opportunities,
  totalSavingsMonthly,
}: ModelChoiceOpportunityTableProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="text-sm font-medium">Model choice opportunities</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">
              Places where a cheaper model appears to preserve outcomes for the same workflow.
            </p>
          </div>
          <div className="rounded-xl border border-border/70 bg-muted/40 px-3 py-2 text-right">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              Potential Monthly Savings
            </p>
            <p className="mt-1 font-display text-2xl tracking-tight">
              {formatCost(totalSavingsMonthly)}
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {opportunities.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No clear model downshift opportunities found for this period yet.
          </p>
        ) : (
          <div className="space-y-3">
            {opportunities.map((opportunity) => (
              <div
                key={`${opportunity.workflow_archetype}:${opportunity.current_model}:${opportunity.recommended_model}`}
                className="rounded-2xl border border-border/70 bg-card/70 p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="outline">
                        {formatLabel(opportunity.workflow_archetype)}
                      </Badge>
                      <Badge
                        variant={confidenceVariant[opportunity.confidence] ?? "outline"}
                      >
                        {formatLabel(opportunity.confidence)} confidence
                      </Badge>
                    </div>
                    <p className="text-base font-semibold">
                      {opportunity.current_model} {"->"} {opportunity.recommended_model}
                    </p>
                    <p className="text-sm text-muted-foreground">{opportunity.rationale}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                      Monthly Savings
                    </p>
                    <p className="mt-1 text-xl font-semibold">
                      {formatCost(opportunity.monthly_savings_estimate)}
                    </p>
                  </div>
                </div>

                <div className="mt-4 grid gap-3 sm:grid-cols-4">
                  <div>
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">
                      Success
                    </p>
                    <p className="mt-1 text-sm">
                      {formatPercent(opportunity.current_success_rate)}
                      {" -> "}
                      {formatPercent(opportunity.recommended_success_rate)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">
                      Avg Cost
                    </p>
                    <p className="mt-1 text-sm">
                      {opportunity.current_avg_cost != null
                        ? formatCost(opportunity.current_avg_cost)
                        : "-"}
                      {" -> "}
                      {opportunity.recommended_avg_cost != null
                        ? formatCost(opportunity.recommended_avg_cost)
                        : "-"}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">
                      Current Sessions
                    </p>
                    <p className="mt-1 text-sm">{opportunity.current_session_count}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">
                      Benchmark Sessions
                    </p>
                    <p className="mt-1 text-sm">{opportunity.supporting_session_count}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
