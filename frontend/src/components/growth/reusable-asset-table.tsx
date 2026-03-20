import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatCost, formatLabel, formatPercent } from "@/lib/utils"
import type { ReusableAssetAnalytics } from "@/types/api"

interface ReusableAssetTableProps {
  assets: ReusableAssetAnalytics[]
}

export function ReusableAssetTable({ assets }: ReusableAssetTableProps) {
  if (assets.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Reusable Skills & Templates</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No reusable skills, commands, or templates detected yet.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Reusable Skills & Templates</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="pb-2 font-medium">Asset</th>
                <th className="pb-2 text-right font-medium">Adoption</th>
                <th className="pb-2 text-right font-medium">Success</th>
                <th className="pb-2 text-right font-medium">Cost / Success</th>
                <th className="pb-2 font-medium">Workflow Fit</th>
                <th className="pb-2 font-medium">Projects</th>
              </tr>
            </thead>
            <tbody>
              {assets.map((asset) => (
                <tr
                  key={`${asset.customization_type}:${asset.identifier}:${asset.provenance}:${asset.source_classification}`}
                  className="border-b border-border/40"
                >
                  <td className="py-2">
                    <div className="space-y-1">
                      <p className="font-mono text-xs">{asset.identifier}</p>
                      <div className="flex flex-wrap gap-2">
                        <Badge variant="outline">{formatLabel(asset.customization_type)}</Badge>
                        <Badge variant="secondary">{formatLabel(asset.provenance)}</Badge>
                        <Badge variant="outline">{formatLabel(asset.source_classification)}</Badge>
                      </div>
                    </div>
                  </td>
                  <td className="py-2 text-right">
                    <div>
                      <p>{formatPercent(asset.adoption_rate)}</p>
                      <p className="text-xs text-muted-foreground">
                        {asset.engineer_count} engineers · {asset.session_count} sessions
                      </p>
                    </div>
                  </td>
                  <td className="py-2 text-right">{formatPercent(asset.success_rate)}</td>
                  <td className="py-2 text-right">
                    {asset.cost_per_successful_outcome != null
                      ? formatCost(asset.cost_per_successful_outcome)
                      : asset.avg_session_cost != null
                        ? formatCost(asset.avg_session_cost)
                        : "-"}
                  </td>
                  <td className="py-2">
                    <div className="flex flex-wrap gap-2">
                      {asset.workflow_archetypes.length === 0 ? (
                        <span className="text-xs text-muted-foreground">No workflow signal yet</span>
                      ) : (
                        asset.workflow_archetypes.map((workflow) => (
                          <Badge key={`${asset.identifier}:${workflow}`} variant="outline">
                            {formatLabel(workflow)}
                          </Badge>
                        ))
                      )}
                    </div>
                  </td>
                  <td className="py-2">
                    <div className="flex flex-wrap gap-2">
                      {asset.top_projects.length === 0 ? (
                        <span className="text-xs text-muted-foreground">No project signal yet</span>
                      ) : (
                        asset.top_projects.map((project) => (
                          <Badge key={`${asset.identifier}:${project}`} variant="outline">
                            {project}
                          </Badge>
                        ))
                      )}
                    </div>
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
