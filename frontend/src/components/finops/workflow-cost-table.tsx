import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { WorkflowCostBreakdown } from "@/types/api"
import { formatCost } from "@/lib/utils"

interface WorkflowCostTableProps {
  rows: WorkflowCostBreakdown[]
}

const DIMENSION_LABELS: Record<string, string> = {
  workflow_archetype: "Workflow Archetype",
  workflow_fingerprint: "Workflow Fingerprint",
}

function formatLabel(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

export function WorkflowCostTable({ rows }: WorkflowCostTableProps) {
  if (rows.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Workflow Cost Attribution</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No workflow cost attribution data available yet.
          </p>
        </CardContent>
      </Card>
    )
  }

  const grouped = rows.reduce<Record<string, WorkflowCostBreakdown[]>>((acc, row) => {
    acc[row.dimension] ??= []
    acc[row.dimension].push(row)
    return acc
  }, {})

  return (
    <Card>
      <CardHeader>
        <CardTitle>Workflow Cost Attribution</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {Object.entries(grouped).map(([dimension, items]) => (
          <section key={dimension} className="space-y-2">
            <h3 className="text-sm font-semibold text-muted-foreground">
              {DIMENSION_LABELS[dimension] ?? formatLabel(dimension)}
            </h3>
            <div className="overflow-x-auto rounded-xl border border-border/60">
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
                  {items.map((row) => (
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
          </section>
        ))}
      </CardContent>
    </Card>
  )
}
