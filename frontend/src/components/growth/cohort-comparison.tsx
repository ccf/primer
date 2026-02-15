import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { CohortMetrics } from "@/types/api"

const cohortColors: Record<string, string> = {
  new_hire: "border-t-blue-500",
  ramping: "border-t-amber-500",
  experienced: "border-t-emerald-500",
}

const cohortLabels: Record<string, string> = {
  new_hire: "New Hire (≤30d)",
  ramping: "Ramping (31–90d)",
  experienced: "Experienced (>90d)",
}

interface CohortComparisonProps {
  cohorts: CohortMetrics[]
}

export function CohortComparison({ cohorts }: CohortComparisonProps) {
  if (cohorts.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">
        No cohort data available yet.
      </div>
    )
  }

  return (
    <div className="grid gap-4 sm:grid-cols-3">
      {cohorts.map((cohort) => (
        <Card key={cohort.cohort_label} className={cn("border-t-4", cohortColors[cohort.cohort_label])}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">
              {cohortLabels[cohort.cohort_label] ?? cohort.cohort_label}
            </CardTitle>
            <p className="text-xs text-muted-foreground">{cohort.engineer_count} engineers</p>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <p className="text-xs text-muted-foreground">Sessions/eng</p>
                <p className="font-medium">{cohort.avg_sessions_per_engineer.toFixed(1)}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Tool diversity</p>
                <p className="font-medium">{cohort.avg_tool_diversity.toFixed(1)}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Success rate</p>
                <p className="font-medium">
                  {cohort.success_rate != null ? `${(cohort.success_rate * 100).toFixed(0)}%` : "—"}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Friction rate</p>
                <p className="font-medium">{cohort.avg_friction_rate.toFixed(2)}</p>
              </div>
            </div>
            {cohort.top_tools.length > 0 && (
              <div>
                <p className="text-xs text-muted-foreground">Top tools</p>
                <p className="text-xs">{cohort.top_tools.slice(0, 3).join(", ")}</p>
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
