import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatDuration } from "@/lib/utils"
import type { EngineerFrictionTimeLost } from "@/types/api"

interface EngineerTimeLostTableProps {
  data: EngineerFrictionTimeLost[]
}

export function EngineerTimeLostTable({ data }: EngineerTimeLostTableProps) {
  if (data.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Time Lost by Engineer</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="pb-2 text-left font-medium">Engineer</th>
                <th className="pb-2 text-right font-medium">Friction Sessions</th>
                <th className="pb-2 text-right font-medium">Friction Count</th>
                <th className="pb-2 text-right font-medium">Time Lost</th>
                <th className="pb-2 text-left font-medium">Top Types</th>
              </tr>
            </thead>
            <tbody>
              {data.map((item) => (
                <tr key={item.engineer_id} className="border-b border-border last:border-0">
                  <td className="py-2 font-medium">{item.engineer_name}</td>
                  <td className="py-2 text-right">{item.sessions_with_friction}</td>
                  <td className="py-2 text-right">{item.total_friction_count}</td>
                  <td className="py-2 text-right">
                    <div>{formatDuration(item.estimated_minutes_lost * 60)}</div>
                    <div className="text-xs text-muted-foreground">
                      {item.avg_minutes_lost_per_friction_session != null
                        ? `${formatDuration(item.avg_minutes_lost_per_friction_session * 60)}/session`
                        : "--"}
                    </div>
                  </td>
                  <td className="py-2">
                    <div className="flex flex-wrap gap-1">
                      {item.top_friction_types.map((frictionType) => (
                        <span
                          key={frictionType}
                          className="inline-flex rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-900/30 dark:text-amber-300"
                        >
                          {frictionType}
                        </span>
                      ))}
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
