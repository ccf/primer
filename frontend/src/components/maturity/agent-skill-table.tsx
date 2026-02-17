import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import type { AgentSkillUsage } from "@/types/api"

interface AgentSkillTableProps {
  data: AgentSkillUsage[]
}

export function AgentSkillTable({ data }: AgentSkillTableProps) {
  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <h3 className="text-sm font-medium">Agents & Skills Usage</h3>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No orchestration or skill tool usage detected yet.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <h3 className="text-sm font-medium">Agents & Skills Usage</h3>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="pb-2 font-medium">Name</th>
                <th className="pb-2 font-medium">Category</th>
                <th className="pb-2 text-right font-medium">Total Calls</th>
                <th className="pb-2 text-right font-medium">Sessions</th>
                <th className="pb-2 text-right font-medium">Engineers</th>
              </tr>
            </thead>
            <tbody>
              {data.map((item) => (
                <tr key={item.name} className="border-b border-border/50">
                  <td className="py-2 font-mono text-xs">{item.name}</td>
                  <td className="py-2">
                    <Badge variant={item.category === "orchestration" ? "default" : "secondary"}>
                      {item.category}
                    </Badge>
                  </td>
                  <td className="py-2 text-right">{item.total_calls.toLocaleString()}</td>
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
