import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatCost, formatLabel, formatPercent } from "@/lib/utils"
import type { ReusableAssetAnalytics } from "@/types/api"

interface ReuseOpportunityCardsProps {
  assets: ReusableAssetAnalytics[]
}

export function ReuseOpportunityCards({ assets }: ReuseOpportunityCardsProps) {
  if (assets.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Underused High-Value Assets</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No high-value reuse opportunities identified yet.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-3">
      <div className="space-y-1">
        <h3 className="text-sm font-medium">Underused High-Value Assets</h3>
        <p className="text-sm text-muted-foreground">
          Reusable assets that perform well but have not spread broadly yet.
        </p>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        {assets.map((asset) => (
          <Card
            key={`${asset.customization_type}:${asset.identifier}:${asset.provenance}:${asset.source_classification}`}
          >
            <CardHeader className="pb-3">
              <div className="space-y-1">
                <CardTitle className="text-base font-mono">{asset.identifier}</CardTitle>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline">{formatLabel(asset.customization_type)}</Badge>
                  <Badge variant="secondary">{formatLabel(asset.provenance)}</Badge>
                  <Badge variant="outline">{formatLabel(asset.source_classification)}</Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid gap-3 sm:grid-cols-3">
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">
                    Adoption
                  </p>
                  <p className="mt-1 text-lg font-semibold">{formatPercent(asset.adoption_rate)}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">
                    Success
                  </p>
                  <p className="mt-1 text-lg font-semibold">{formatPercent(asset.success_rate)}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">
                    Cost / Success
                  </p>
                  <p className="mt-1 text-lg font-semibold">
                    {asset.cost_per_successful_outcome != null
                      ? formatCost(asset.cost_per_successful_outcome)
                      : "-"}
                  </p>
                </div>
              </div>

              <div className="space-y-2">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">
                  Workflow Fit
                </p>
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
              </div>

              {asset.top_projects.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">
                    Example Projects
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {asset.top_projects.map((project) => (
                      <Badge key={`${asset.identifier}:${project}`} variant="outline">
                        {project}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
