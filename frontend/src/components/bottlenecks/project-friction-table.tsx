import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { ProjectFriction } from "@/types/api"

interface ProjectFrictionTableProps {
  data: ProjectFriction[]
}

export function ProjectFrictionTable({ data }: ProjectFrictionTableProps) {
  if (data.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Project Friction</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="pb-2 text-left font-medium">Project</th>
                <th className="pb-2 text-right font-medium">Sessions</th>
                <th className="pb-2 text-right font-medium">Friction Sessions</th>
                <th className="pb-2 text-right font-medium">Friction Rate</th>
                <th className="pb-2 text-left font-medium">Top Types</th>
              </tr>
            </thead>
            <tbody>
              {data.map((item) => (
                <tr key={item.project_name} className="border-b border-border last:border-0">
                  <td className="py-2 font-medium">{item.project_name}</td>
                  <td className="py-2 text-right">{item.total_sessions}</td>
                  <td className="py-2 text-right">{item.sessions_with_friction}</td>
                  <td className="py-2 text-right">{(item.friction_rate * 100).toFixed(0)}%</td>
                  <td className="py-2">
                    <div className="flex flex-wrap gap-1">
                      {item.top_friction_types.map((ft) => (
                        <span
                          key={ft}
                          className="inline-flex rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-900/30 dark:text-amber-300"
                        >
                          {ft}
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
