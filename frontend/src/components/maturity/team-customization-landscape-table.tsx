import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { formatPercent } from "@/lib/utils"
import type { TeamCustomizationLandscape } from "@/types/api"

interface TeamCustomizationLandscapeTableProps {
  data: TeamCustomizationLandscape[]
}

export function TeamCustomizationLandscapeTable({ data }: TeamCustomizationLandscapeTableProps) {
  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Cross-Team Tooling Landscape</CardTitle>
          <CardDescription>No cross-team customization landscape available yet.</CardDescription>
        </CardHeader>
        <CardContent />
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Cross-Team Tooling Landscape</CardTitle>
        <CardDescription>
          See where teams converge, where they diverge, and which customizations are spreading.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto rounded-2xl border border-border/60 bg-background">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="px-4 py-3 font-medium">Team</th>
                <th className="px-4 py-3 text-right font-medium">Adoption</th>
                <th className="px-4 py-3 text-right font-medium">Customizations</th>
                <th className="px-4 py-3 font-medium">Top Customizations</th>
                <th className="px-4 py-3 font-medium">Unique Differentiators</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row) => (
                <tr key={row.team_id} className="border-b border-border/40">
                  <td className="px-4 py-3">
                    <div className="space-y-1">
                      <p className="font-medium">{row.team_name}</p>
                      <p className="text-xs text-muted-foreground">
                        {row.engineers_using_explicit_customizations}/{row.engineer_count} engineers
                      </p>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right">{formatPercent(row.adoption_rate)}</td>
                  <td className="px-4 py-3 text-right">{row.explicit_customization_count}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      {row.top_customizations.map((item) => (
                        <Badge key={`${row.team_id}:${item}`} variant="secondary">
                          {item}
                        </Badge>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      {row.unique_customizations.length === 0 ? (
                        <span className="text-xs text-muted-foreground">No unique differentiators yet</span>
                      ) : (
                        row.unique_customizations.map((item) => (
                          <Badge key={`${row.team_id}:unique:${item}`} variant="outline">
                            {item}
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
