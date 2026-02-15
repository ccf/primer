import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import type { EngineerToolProfile } from "@/types/api"

interface EngineerToolTableProps {
  data: EngineerToolProfile[]
}

export function EngineerToolTable({ data }: EngineerToolTableProps) {
  if (data.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Engineer Tool Profiles</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="pb-2 text-left font-medium text-muted-foreground">Engineer</th>
                <th className="pb-2 text-left font-medium text-muted-foreground">Tools Used</th>
                <th className="pb-2 text-left font-medium text-muted-foreground">Total Calls</th>
                <th className="pb-2 text-left font-medium text-muted-foreground">Top Tools</th>
              </tr>
            </thead>
            <tbody>
              {data.map((eng) => (
                <tr key={eng.engineer_id} className="border-b border-border last:border-0">
                  <td className="py-2.5">{eng.name}</td>
                  <td className="py-2.5">{eng.tools_used}</td>
                  <td className="py-2.5">{eng.total_tool_calls.toLocaleString()}</td>
                  <td className="py-2.5">
                    <div className="flex flex-wrap gap-1">
                      {eng.top_tools.slice(0, 5).map((tool) => (
                        <Badge key={tool} variant="secondary" className="text-[10px]">
                          {tool}
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
