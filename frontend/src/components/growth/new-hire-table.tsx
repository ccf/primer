import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { NewHireProgress } from "@/types/api"

interface NewHireTableProps {
  progress: NewHireProgress[]
}

export function NewHireTable({ progress }: NewHireTableProps) {
  if (progress.length === 0) {
    return null
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">New Hire Progress</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-muted-foreground">
                <th className="pb-2 pr-4">Engineer</th>
                <th className="pb-2 pr-4">Days</th>
                <th className="pb-2 pr-4">Sessions</th>
                <th className="pb-2 pr-4">Tools</th>
                <th className="pb-2 pr-4">Success</th>
                <th className="pb-2 pr-4">Velocity</th>
                <th className="pb-2">Lagging Areas</th>
              </tr>
            </thead>
            <tbody>
              {progress.map((nhp) => (
                <tr key={nhp.engineer_id} className="border-b border-border last:border-0">
                  <td className="py-2 pr-4 font-medium">{nhp.name}</td>
                  <td className="py-2 pr-4">{nhp.days_since_first_session}d</td>
                  <td className="py-2 pr-4">{nhp.total_sessions}</td>
                  <td className="py-2 pr-4">{nhp.tool_diversity}</td>
                  <td className="py-2 pr-4">
                    {nhp.success_rate != null ? `${(nhp.success_rate * 100).toFixed(0)}%` : "—"}
                  </td>
                  <td className="py-2 pr-4">
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-16 rounded-full bg-secondary">
                        <div
                          className={cn(
                            "h-2 rounded-full",
                            nhp.velocity_score >= 70
                              ? "bg-success"
                              : nhp.velocity_score >= 40
                                ? "bg-warning"
                                : "bg-destructive",
                          )}
                          style={{ width: `${nhp.velocity_score}%` }}
                        />
                      </div>
                      <span className="text-xs">{nhp.velocity_score.toFixed(0)}</span>
                    </div>
                  </td>
                  <td className="py-2">
                    <div className="flex flex-wrap gap-1">
                      {nhp.lagging_areas.map((area) => (
                        <Badge key={area} variant="warning">
                          {area}
                        </Badge>
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
