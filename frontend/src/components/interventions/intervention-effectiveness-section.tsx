import { CheckCircle2, Clock3, Gauge, TrendingUp } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { InlineStat } from "@/components/ui/inline-stat"
import { formatCost, formatPercent } from "@/lib/utils"
import type {
  InterventionEffectivenessGroup,
  InterventionEffectivenessResponse,
} from "@/types/api"

interface InterventionEffectivenessSectionProps {
  data: InterventionEffectivenessResponse
}

function formatSignedDelta(value: number | null | undefined, suffix = ""): string {
  if (value == null) return "-"
  const sign = value > 0 ? "+" : ""
  return `${sign}${value.toFixed(1)}${suffix}`
}

function formatSignedPercentPoints(value: number | null | undefined): string {
  if (value == null) return "-"
  const points = value * 100
  const sign = points > 0 ? "+" : ""
  return `${sign}${points.toFixed(0)} pts`
}

function formatSignedCost(value: number | null | undefined): string {
  if (value == null) return "-"
  const sign = value > 0 ? "+" : ""
  return `${sign}${formatCost(value)}`
}

function formatCompletionDays(value: number | null | undefined): string {
  if (value == null) return "-"
  return `${value.toFixed(1)}d`
}

function EffectivenessTable({
  title,
  labelHeader,
  rows,
}: {
  title: string
  labelHeader: string
  rows: InterventionEffectivenessGroup[]
}) {
  if (rows.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No completed interventions with measurable impact are available yet.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="pb-2 text-left font-medium">{labelHeader}</th>
                <th className="pb-2 text-right font-medium">Completed</th>
                <th className="pb-2 text-right font-medium">Improvement Rate</th>
                <th className="pb-2 text-right font-medium">Success Uplift</th>
                <th className="pb-2 text-right font-medium">Friction Drop</th>
                <th className="pb-2 text-right font-medium">Findings Drop</th>
                <th className="pb-2 text-right font-medium">Cost Reduction</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.key} className="border-b border-border last:border-0">
                  <td className="py-2 font-medium">{row.label}</td>
                  <td className="py-2 text-right">{row.completed_interventions}</td>
                  <td className="py-2 text-right">{formatPercent(row.improvement_rate)}</td>
                  <td className="py-2 text-right">
                    {formatSignedPercentPoints(row.avg_success_rate_delta)}
                  </td>
                  <td className="py-2 text-right">{formatSignedDelta(row.avg_friction_delta)}</td>
                  <td className="py-2 text-right">
                    {formatSignedDelta(row.avg_findings_per_pr_delta)}
                  </td>
                  <td className="py-2 text-right">
                    {formatSignedCost(row.avg_cost_per_session_delta)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

export function InterventionEffectivenessSection({
  data,
}: InterventionEffectivenessSectionProps) {
  return (
    <section className="space-y-6">
      <div className="space-y-1">
        <h2 className="text-lg font-semibold">Effectiveness</h2>
        <p className="text-sm text-muted-foreground">
          Measure whether completed interventions actually improved outcomes across teams,
          projects, and engineer cohorts.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <InlineStat
          label="Completed"
          value={String(data.summary.completed_interventions)}
          icon={CheckCircle2}
        />
        <InlineStat
          label="Measured"
          value={String(data.summary.measured_interventions)}
          icon={Gauge}
        />
        <InlineStat
          label="Improvement Rate"
          value={formatPercent(data.summary.improvement_rate)}
          icon={TrendingUp}
        />
        <InlineStat
          label="Avg Completion Time"
          value={formatCompletionDays(data.summary.avg_completion_days)}
          icon={Clock3}
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <EffectivenessTable title="By Team" labelHeader="Team" rows={data.by_team} />
        <EffectivenessTable title="By Project" labelHeader="Project" rows={data.by_project} />
        <EffectivenessTable
          title="By Engineer Cohort"
          labelHeader="Cohort"
          rows={data.by_engineer_cohort}
        />
      </div>
    </section>
  )
}
