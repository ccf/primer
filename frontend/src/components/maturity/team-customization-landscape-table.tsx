import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { formatLabel, formatPercent } from "@/lib/utils"
import type { TeamCustomizationLandscape } from "@/types/api"

interface TeamCustomizationLandscapeTableProps {
  data: TeamCustomizationLandscape[]
}

export function TeamCustomizationLandscapeTable({ data }: TeamCustomizationLandscapeTableProps) {
  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <h3 className="text-sm font-medium">Cross-Team Tooling Landscape</h3>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No cross-team customization landscape available yet.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <h3 className="text-sm font-medium">Cross-Team Tooling Landscape</h3>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="pb-2 font-medium">Team</th>
                <th className="pb-2 text-right font-medium">Adoption</th>
                <th className="pb-2 text-right font-medium">Customizations</th>
                <th className="pb-2 font-medium">Top Customizations</th>
                <th className="pb-2 font-medium">Unique Differentiators</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row) => (
                <tr key={row.team_id} className="border-b border-border/40">
                  <td className="py-2">
                    <div className="space-y-1">
                      <p className="font-medium">{row.team_name}</p>
                      <p className="text-xs text-muted-foreground">
                        {row.engineers_using_explicit_customizations}/{row.engineer_count} engineers
                      </p>
                    </div>
                  </td>
                  <td className="py-2 text-right">{formatPercent(row.adoption_rate)}</td>
                  <td className="py-2 text-right">{row.explicit_customization_count}</td>
                  <td className="py-2">
                    <div className="flex flex-wrap gap-2">
                      {row.top_customizations.map((item) => (
                        <Badge key={`${row.team_id}:${item}`} variant="secondary">
                          {item}
                        </Badge>
                      ))}
                    </div>
                  </td>
                  <td className="py-2">
                    <div className="flex flex-wrap gap-2">
                      {row.unique_customizations.length === 0 ? (
                        <span className="text-xs text-muted-foreground">No unique differentiators yet</span>
                      ) : (
                        row.unique_customizations.map((item) => (
                          <Badge key={`${row.team_id}:unique:${item}`} variant="outline">
                            {formatLabel(item)}
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
