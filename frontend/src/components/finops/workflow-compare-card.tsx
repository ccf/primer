import { useState } from "react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatCost, formatLabel, formatPercent } from "@/lib/utils"
import type { QualityAttributionRow, WorkflowCostBreakdown } from "@/types/api"

type CompareDimension = "workflow_archetype" | "workflow_fingerprint"

interface WorkflowCompareCardProps {
  workflowCosts: WorkflowCostBreakdown[]
  qualityRows: QualityAttributionRow[]
}

const DIMENSION_LABELS: Record<CompareDimension, string> = {
  workflow_archetype: "Workflow Archetype",
  workflow_fingerprint: "Workflow Fingerprint",
}

function displayLabel(value: string, dimension: CompareDimension) {
  return dimension === "workflow_archetype" ? formatLabel(value) : value
}

function formatMetric(value: number | null | undefined, digits = 1): string {
  return value == null ? "-" : value.toFixed(digits)
}

export function WorkflowCompareCard({
  workflowCosts,
  qualityRows,
}: WorkflowCompareCardProps) {
  const [dimension, setDimension] = useState<CompareDimension>("workflow_archetype")
  const [leftLabel, setLeftLabel] = useState("")
  const [rightLabel, setRightLabel] = useState("")

  const options = workflowCosts.filter((row) => row.dimension === dimension)
  const labels = options.map((row) => row.label)
  const effectiveLeftLabel = labels.includes(leftLabel) ? leftLabel : (labels[0] ?? "")
  const effectiveRightLabel =
    labels.includes(rightLabel) && rightLabel !== effectiveLeftLabel
      ? rightLabel
      : (labels.find((label) => label !== effectiveLeftLabel) ?? "")

  if (options.length < 2) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Workflow Compare</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Need at least two workflows with cost data to compare them.
          </p>
        </CardContent>
      </Card>
    )
  }

  const costMap = Object.fromEntries(
    workflowCosts
      .filter((row) => row.dimension === dimension)
      .map((row) => [row.label, row]),
  )
  const qualityMap = Object.fromEntries(
    qualityRows
      .filter((row) => row.dimension === dimension)
      .map((row) => [row.label, row]),
  )

  const leftCost = costMap[effectiveLeftLabel]
  const rightCost = costMap[effectiveRightLabel]
  const leftQuality = qualityMap[effectiveLeftLabel]
  const rightQuality = qualityMap[effectiveRightLabel]

  if (!leftCost || !rightCost) {
    return null
  }

  return (
    <Card>
      <CardHeader className="pb-4">
        <CardTitle>Workflow Compare</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 md:grid-cols-3">
          <label className="space-y-1">
            <span className="text-xs font-medium text-muted-foreground">Dimension</span>
            <select
              value={dimension}
              onChange={(e) => setDimension(e.target.value as CompareDimension)}
              className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
            >
              <option value="workflow_archetype">{DIMENSION_LABELS.workflow_archetype}</option>
              <option value="workflow_fingerprint">{DIMENSION_LABELS.workflow_fingerprint}</option>
            </select>
          </label>

          <label className="space-y-1">
            <span className="text-xs font-medium text-muted-foreground">Workflow A</span>
            <select
              value={effectiveLeftLabel}
              onChange={(e) => setLeftLabel(e.target.value)}
              className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
            >
              {options.map((row) => (
                <option key={`left-${row.label}`} value={row.label}>
                  {displayLabel(row.label, dimension)}
                </option>
              ))}
            </select>
          </label>

          <label className="space-y-1">
            <span className="text-xs font-medium text-muted-foreground">Workflow B</span>
            <select
              value={effectiveRightLabel}
              onChange={(e) => setRightLabel(e.target.value)}
              className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
            >
              {options.map((row) => (
                <option key={`right-${row.label}`} value={row.label}>
                  {displayLabel(row.label, dimension)}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="overflow-x-auto rounded-xl border border-border/60">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/50 text-left text-xs font-medium text-muted-foreground">
                <th className="px-3 py-2">Metric</th>
                <th className="px-3 py-2">{displayLabel(effectiveLeftLabel, dimension)}</th>
                <th className="px-3 py-2">{displayLabel(effectiveRightLabel, dimension)}</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border/40">
                <td className="px-3 py-2 font-medium">Sessions</td>
                <td className="px-3 py-2">{leftCost.session_count}</td>
                <td className="px-3 py-2">{rightCost.session_count}</td>
              </tr>
              <tr className="border-b border-border/40">
                <td className="px-3 py-2 font-medium">Total Cost</td>
                <td className="px-3 py-2">{formatCost(leftCost.total_estimated_cost)}</td>
                <td className="px-3 py-2">{formatCost(rightCost.total_estimated_cost)}</td>
              </tr>
              <tr className="border-b border-border/40">
                <td className="px-3 py-2 font-medium">Avg Cost / Session</td>
                <td className="px-3 py-2">
                  {leftCost.avg_cost_per_session != null ? formatCost(leftCost.avg_cost_per_session) : "-"}
                </td>
                <td className="px-3 py-2">
                  {rightCost.avg_cost_per_session != null ? formatCost(rightCost.avg_cost_per_session) : "-"}
                </td>
              </tr>
              <tr className="border-b border-border/40">
                <td className="px-3 py-2 font-medium">Cost / Success</td>
                <td className="px-3 py-2">
                  {leftCost.cost_per_successful_outcome != null
                    ? formatCost(leftCost.cost_per_successful_outcome)
                    : "-"}
                </td>
                <td className="px-3 py-2">
                  {rightCost.cost_per_successful_outcome != null
                    ? formatCost(rightCost.cost_per_successful_outcome)
                    : "-"}
                </td>
              </tr>
              <tr className="border-b border-border/40">
                <td className="px-3 py-2 font-medium">Linked PRs</td>
                <td className="px-3 py-2">{leftQuality?.linked_prs ?? "-"}</td>
                <td className="px-3 py-2">{rightQuality?.linked_prs ?? "-"}</td>
              </tr>
              <tr className="border-b border-border/40">
                <td className="px-3 py-2 font-medium">Merge Rate</td>
                <td className="px-3 py-2">{formatPercent(leftQuality?.merge_rate)}</td>
                <td className="px-3 py-2">{formatPercent(rightQuality?.merge_rate)}</td>
              </tr>
              <tr className="border-b border-border/40">
                <td className="px-3 py-2 font-medium">Reviews / PR</td>
                <td className="px-3 py-2">{formatMetric(leftQuality?.avg_review_comments_per_pr)}</td>
                <td className="px-3 py-2">{formatMetric(rightQuality?.avg_review_comments_per_pr)}</td>
              </tr>
              <tr className="border-b border-border/40">
                <td className="px-3 py-2 font-medium">Findings / PR</td>
                <td className="px-3 py-2">{formatMetric(leftQuality?.avg_findings_per_pr)}</td>
                <td className="px-3 py-2">{formatMetric(rightQuality?.avg_findings_per_pr)}</td>
              </tr>
              <tr>
                <td className="px-3 py-2 font-medium">Merge Time (h)</td>
                <td className="px-3 py-2">{formatMetric(leftQuality?.avg_time_to_merge_hours)}</td>
                <td className="px-3 py-2">{formatMetric(rightQuality?.avg_time_to_merge_hours)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}
