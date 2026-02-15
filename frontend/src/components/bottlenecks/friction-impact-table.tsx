import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { FrictionImpact } from "@/types/api"

interface FrictionImpactTableProps {
  data: FrictionImpact[]
}

function ImpactBadge({ score }: { score: number | null }) {
  if (score == null) return <span className="text-muted-foreground">--</span>

  const abs = Math.abs(score)
  let color = "text-muted-foreground"
  if (abs >= 0.2) color = "text-red-600 dark:text-red-400"
  else if (abs >= 0.1) color = "text-amber-600 dark:text-amber-400"
  else if (abs > 0) color = "text-yellow-600 dark:text-yellow-400"

  return <span className={cn("font-medium", color)}>{(score * 100).toFixed(1)}pp</span>
}

export function FrictionImpactTable({ data }: FrictionImpactTableProps) {
  if (data.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Friction Impact Analysis</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="pb-2 text-left font-medium">Friction Type</th>
                <th className="pb-2 text-right font-medium">Occurrences</th>
                <th className="pb-2 text-right font-medium">Sessions</th>
                <th className="pb-2 text-right font-medium">Success w/</th>
                <th className="pb-2 text-right font-medium">Success w/o</th>
                <th className="pb-2 text-right font-medium">Impact</th>
              </tr>
            </thead>
            <tbody>
              {data.map((item) => (
                <tr key={item.friction_type} className="border-b border-border last:border-0">
                  <td className="py-2 font-medium">{item.friction_type}</td>
                  <td className="py-2 text-right">{item.occurrence_count}</td>
                  <td className="py-2 text-right">{item.sessions_affected}</td>
                  <td className="py-2 text-right">
                    {item.success_rate_with != null
                      ? `${(item.success_rate_with * 100).toFixed(0)}%`
                      : "--"}
                  </td>
                  <td className="py-2 text-right">
                    {item.success_rate_without != null
                      ? `${(item.success_rate_without * 100).toFixed(0)}%`
                      : "--"}
                  </td>
                  <td className="py-2 text-right">
                    <ImpactBadge score={item.impact_score} />
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
