import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import type { WorkflowCostBreakdown } from "@/types/api"
import { formatCost, formatLabel } from "@/lib/utils"

interface WorkflowCostTableProps {
  rows: WorkflowCostBreakdown[]
}

const DIMENSION_LABELS: Record<string, string> = {
  workflow_archetype: "Workflow Archetype",
  workflow_fingerprint: "Workflow Fingerprint",
}

const DEFAULT_VISIBLE = 10

export function WorkflowCostTable({ rows }: WorkflowCostTableProps) {
  const [expandedDimensions, setExpandedDimensions] = useState<Set<string>>(new Set())

  if (rows.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Workflow Cost Attribution</CardTitle>
          <CardDescription>
            No workflow cost attribution data available yet.
          </CardDescription>
        </CardHeader>
        <CardContent />
      </Card>
    )
  }

  const grouped = rows.reduce<Record<string, WorkflowCostBreakdown[]>>((acc, row) => {
    acc[row.dimension] ??= []
    acc[row.dimension].push(row)
    return acc
  }, {})

  // Sort each group by total cost descending
  for (const items of Object.values(grouped)) {
    items.sort((a, b) => (b.total_estimated_cost ?? 0) - (a.total_estimated_cost ?? 0))
  }

  const toggleDimension = (dimension: string) => {
    setExpandedDimensions((prev) => {
      const next = new Set(prev)
      if (next.has(dimension)) {
        next.delete(dimension)
      } else {
        next.add(dimension)
      }
      return next
    })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Workflow Cost Attribution</CardTitle>
        <CardDescription>
          Where spend clusters around reusable workflow patterns, sorted by total cost.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {Object.entries(grouped).map(([dimension, items]) => {
          const isExpanded = expandedDimensions.has(dimension)
          const visibleItems = isExpanded ? items : items.slice(0, DEFAULT_VISIBLE)
          const hasMore = items.length > DEFAULT_VISIBLE

          return (
            <section key={dimension} className="space-y-3 rounded-2xl border border-border/60 bg-muted/20 p-4">
              <div className="flex items-center justify-between gap-3">
                <h3 className="text-sm font-semibold text-foreground">
                  {DIMENSION_LABELS[dimension] ?? formatLabel(dimension)}
                </h3>
                <span className="text-xs text-muted-foreground">
                  {isExpanded ? items.length : `Top ${visibleItems.length} of ${items.length}`} pattern{items.length === 1 ? "" : "s"}
                </span>
              </div>
              <div className="overflow-x-auto rounded-xl border border-border/60 bg-background">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border bg-muted/50 text-left text-xs font-medium text-muted-foreground">
                      <th className="px-3 py-2">Workflow</th>
                      <th className="px-3 py-2">Sessions</th>
                      <th className="px-3 py-2">Total Cost</th>
                      <th className="px-3 py-2">Avg Cost / Session</th>
                      <th className="px-3 py-2">Cost / Success</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleItems.map((row) => (
                      <tr key={`${row.dimension}-${row.label}`} className="border-b border-border/40 last:border-0">
                        <td className="px-3 py-2 font-medium">{formatLabel(row.label)}</td>
                        <td className="px-3 py-2">{row.session_count}</td>
                        <td className="px-3 py-2">{formatCost(row.total_estimated_cost)}</td>
                        <td className="px-3 py-2">
                          {row.avg_cost_per_session != null ? formatCost(row.avg_cost_per_session) : "-"}
                        </td>
                        <td className="px-3 py-2">
                          {row.cost_per_successful_outcome != null
                            ? formatCost(row.cost_per_successful_outcome)
                            : "-"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {hasMore && (
                <button
                  type="button"
                  onClick={() => toggleDimension(dimension)}
                  className="text-xs text-primary hover:underline"
                >
                  {isExpanded ? "Show top 10" : `Show all ${items.length} patterns`}
                </button>
              )}
            </section>
          )
        })}
      </CardContent>
    </Card>
  )
}
