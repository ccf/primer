import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { formatLabel } from "@/lib/utils"
import type { CustomizationUsage } from "@/types/api"

interface CustomizationBreakdownTableProps {
  data: CustomizationUsage[]
}

export function CustomizationBreakdownTable({ data }: CustomizationBreakdownTableProps) {
  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <h3 className="text-sm font-medium">Explicit Customizations</h3>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No explicit MCPs, skills, or subagents detected yet.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <h3 className="text-sm font-medium">Explicit Customizations</h3>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="pb-2 font-medium">Identifier</th>
                <th className="pb-2 font-medium">Type</th>
                <th className="pb-2 font-medium">Provenance</th>
                <th className="pb-2 font-medium">Source</th>
                <th className="pb-2 text-right font-medium">Invocations</th>
                <th className="pb-2 text-right font-medium">Sessions</th>
                <th className="pb-2 text-right font-medium">Engineers</th>
              </tr>
            </thead>
            <tbody>
              {data.map((item) => (
                <tr
                  key={`${item.customization_type}:${item.identifier}:${item.provenance}:${item.source_classification}`}
                  className="border-b border-border/40"
                >
                  <td className="py-2 font-mono text-xs">{item.identifier}</td>
                  <td className="py-2">
                    <Badge variant="outline">{formatLabel(item.customization_type)}</Badge>
                  </td>
                  <td className="py-2">
                    <Badge variant="secondary">{formatLabel(item.provenance)}</Badge>
                  </td>
                  <td className="py-2">
                    <Badge variant="outline">{formatLabel(item.source_classification)}</Badge>
                  </td>
                  <td className="py-2 text-right">{item.total_invocations.toLocaleString()}</td>
                  <td className="py-2 text-right">{item.session_count}</td>
                  <td className="py-2 text-right">{item.engineer_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}
