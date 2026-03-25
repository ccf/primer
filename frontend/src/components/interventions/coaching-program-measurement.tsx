import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { formatCost } from "@/lib/utils"
import type { CoachingProgramMeasurement } from "@/types/api"

interface CoachingProgramMeasurementProps {
  programs: CoachingProgramMeasurement[]
}

function formatSignedPercentPoints(value: number | null | undefined): string {
  if (value == null) return "-"
  const points = value * 100
  const sign = points > 0 ? "+" : ""
  return `${sign}${points.toFixed(0)} pts`
}

function formatSignedDelta(value: number | null | undefined): string {
  if (value == null) return "-"
  const sign = value > 0 ? "+" : ""
  return `${sign}${value.toFixed(1)}`
}

function formatSignedCost(value: number | null | undefined): string {
  if (value == null) return "-"
  const sign = value > 0 ? "+" : value < 0 ? "-" : ""
  return `${sign}${formatCost(Math.abs(value))}`
}

export function CoachingProgramMeasurementSection({
  programs,
}: CoachingProgramMeasurementProps) {
  if (programs.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Coaching Program Measurement</CardTitle>
          <CardDescription>
            No measured onboarding or training programs are available yet.
          </CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <section className="space-y-4">
      <div className="space-y-1">
        <h2 className="font-display text-xl tracking-tight">Coaching Program Measurement</h2>
        <p className="text-sm text-muted-foreground">
          See which onboarding and training changes actually improved outcomes.
        </p>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        {programs.map((program) => (
          <Card key={program.intervention_id} className="overflow-hidden">
            <div className="h-1 bg-gradient-to-r from-primary/60 via-primary/20 to-transparent" />
            <CardHeader className="space-y-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-1">
                  <CardTitle className="text-base">{program.title}</CardTitle>
                  <CardDescription>
                    {program.target_cohort ?? "General cohort"}
                    {program.project_name ? ` • ${program.project_name}` : ""}
                    {program.owner_name ? ` • ${program.owner_name}` : ""}
                  </CardDescription>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge variant={program.improved ? "success" : "outline"}>
                    {program.improved ? "Improved" : "Mixed"}
                  </Badge>
                  <Badge variant={program.measured ? "secondary" : "outline"}>
                    {program.measured ? "Measured" : "Unmeasured"}
                  </Badge>
                </div>
              </div>
              {program.hypothesis ? (
                <p className="text-sm text-muted-foreground">{program.hypothesis}</p>
              ) : null}
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-2xl border border-border/60 bg-muted/20 p-3">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">
                    Success
                  </p>
                  <p className="mt-1 font-display text-2xl">
                    {formatSignedPercentPoints(program.success_rate_delta)}
                  </p>
                </div>
                <div className="rounded-2xl border border-border/60 bg-muted/20 p-3">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">
                    Friction
                  </p>
                  <p className="mt-1 font-display text-2xl">
                    {formatSignedDelta(program.friction_delta)}
                  </p>
                </div>
                <div className="rounded-2xl border border-border/60 bg-muted/20 p-3">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">
                    Findings / PR
                  </p>
                  <p className="mt-1 font-display text-2xl">
                    {formatSignedDelta(program.findings_per_pr_delta)}
                  </p>
                </div>
                <div className="rounded-2xl border border-border/60 bg-muted/20 p-3">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">
                    Cost / Session
                  </p>
                  <p className="mt-1 font-display text-2xl">
                    {formatSignedCost(program.avg_cost_per_session_delta)}
                  </p>
                </div>
              </div>

              {program.success_criteria ? (
                <div className="rounded-2xl border border-border/60 bg-background p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Success Criteria
                  </p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {program.success_criteria}
                  </p>
                </div>
              ) : null}
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  )
}
