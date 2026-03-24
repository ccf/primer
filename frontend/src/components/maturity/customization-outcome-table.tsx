import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
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
          <CardTitle className="text-base">Customization Outcome Attribution</CardTitle>
          <CardDescription>No customization outcome attribution available yet.</CardDescription>
        </CardHeader>
        <CardContent />
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Customization Outcome Attribution</CardTitle>
        <CardDescription>
          See which explicit customizations and stacks are associated with better outcomes, not just more usage.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto rounded-2xl border border-border/60 bg-background">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="px-4 py-3 font-medium">Label</th>
                <th className="px-4 py-3 font-medium">Dimension</th>
                <th className="px-4 py-3 font-medium">Details</th>
                <th className="px-4 py-3 text-right font-medium">Engineers</th>
                <th className="px-4 py-3 text-right font-medium">Success</th>
                <th className="px-4 py-3 text-right font-medium">Merge Rate</th>
                <th className="px-4 py-3 text-right font-medium">Cost / Success</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={`${row.dimension}:${row.label}:${index}`} className="border-b border-border/40">
                  <td className="px-4 py-3">
                    <div className="space-y-1">
                      <p className="font-medium">{row.label}</p>
                      <p className="text-xs text-muted-foreground">
                        {row.support_session_count} sessions • {formatPercent(row.cohort_share)}
                      </p>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant="outline">{formatLabel(row.dimension)}</Badge>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      {row.customization_type && (
                        <Badge variant="outline">{formatLabel(row.customization_type)}</Badge>
                      )}
                      {row.provenance && (
                        <Badge variant="secondary">{formatLabel(row.provenance)}</Badge>
                      )}
                      {row.source_classification && (
                        <Badge variant="outline">{formatLabel(row.source_classification)}</Badge>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right">{row.support_engineer_count}</td>
                  <td className="px-4 py-3 text-right">{formatPercent(row.avg_success_rate)}</td>
                  <td className="px-4 py-3 text-right">{formatPercent(row.avg_pr_merge_rate)}</td>
                  <td className="px-4 py-3 text-right">
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
