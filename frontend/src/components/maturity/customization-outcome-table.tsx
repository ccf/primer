import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { formatCost, formatLabel, formatPercent } from "@/lib/utils"
import type { CustomizationOutcomeAttribution } from "@/types/api"

interface CustomizationOutcomeTableProps {
  rows: CustomizationOutcomeAttribution[]
}

export function CustomizationOutcomeTable({ rows }: CustomizationOutcomeTableProps) {
  if (rows.length === 0) {
    return (
      <Card>
        <CardHeader>
          <h3 className="text-sm font-medium">Customization Outcome Attribution</h3>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No customization outcome attribution available yet.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <h3 className="text-sm font-medium">Customization Outcome Attribution</h3>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="pb-2 font-medium">Label</th>
                <th className="pb-2 font-medium">Dimension</th>
                <th className="pb-2 font-medium">Details</th>
                <th className="pb-2 text-right font-medium">Engineers</th>
                <th className="pb-2 text-right font-medium">Success</th>
                <th className="pb-2 text-right font-medium">Merge Rate</th>
                <th className="pb-2 text-right font-medium">Cost / Success</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={`${row.dimension}:${row.label}:${index}`} className="border-b border-border/40">
                  <td className="py-2">
                    <div className="space-y-1">
                      <p className="font-medium">{row.label}</p>
                      <p className="text-xs text-muted-foreground">
                        {row.support_session_count} sessions • {formatPercent(row.cohort_share)}
                      </p>
                    </div>
                  </td>
                  <td className="py-2">
                    <Badge variant="outline">{formatLabel(row.dimension)}</Badge>
                  </td>
                  <td className="py-2">
                    <div className="flex flex-wrap gap-2">
                      {row.customization_type && (
                        <Badge variant="outline">{formatLabel(row.customization_type)}</Badge>
                      )}
                      {row.provenance && (
                        <Badge variant="secondary">{formatLabel(row.provenance)}</Badge>
                      )}
                    </div>
                  </td>
                  <td className="py-2 text-right">{row.support_engineer_count}</td>
                  <td className="py-2 text-right">{formatPercent(row.avg_success_rate)}</td>
                  <td className="py-2 text-right">{formatPercent(row.avg_pr_merge_rate)}</td>
                  <td className="py-2 text-right">
                    {row.avg_cost_per_successful_outcome != null
                      ? formatCost(row.avg_cost_per_successful_outcome)
                      : "-"}
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
