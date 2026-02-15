import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { EngineerSkillProfile } from "@/types/api"

const proficiencyStyles: Record<string, string> = {
  expert: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
  proficient: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  moderate: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  novice: "bg-secondary text-secondary-foreground",
}

interface EngineerSkillTableProps {
  data: EngineerSkillProfile[]
}

export function EngineerSkillTable({ data }: EngineerSkillTableProps) {
  if (data.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Engineer Skill Profiles</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="pb-2 text-left font-medium text-muted-foreground">Engineer</th>
                <th className="pb-2 text-left font-medium text-muted-foreground">Sessions</th>
                <th className="pb-2 text-left font-medium text-muted-foreground">Projects</th>
                <th className="pb-2 text-left font-medium text-muted-foreground">Diversity</th>
                <th className="pb-2 text-left font-medium text-muted-foreground">Session Types</th>
                <th className="pb-2 text-left font-medium text-muted-foreground">Tool Proficiency</th>
              </tr>
            </thead>
            <tbody>
              {data.map((eng) => (
                <tr key={eng.engineer_id} className="border-b border-border last:border-0">
                  <td className="py-2.5 font-medium">{eng.name}</td>
                  <td className="py-2.5">{eng.total_sessions}</td>
                  <td className="py-2.5">{eng.project_count}</td>
                  <td className="py-2.5">{eng.diversity_score.toFixed(2)}</td>
                  <td className="py-2.5">
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(eng.session_types)
                        .sort(([, a], [, b]) => b - a)
                        .slice(0, 4)
                        .map(([type, count]) => (
                          <Badge key={type} variant="secondary" className="text-[10px]">
                            {type} ({count})
                          </Badge>
                        ))}
                    </div>
                  </td>
                  <td className="py-2.5">
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(eng.tool_proficiency)
                        .sort(([, a], [, b]) => {
                          const order = ["expert", "proficient", "moderate", "novice"]
                          return order.indexOf(a) - order.indexOf(b)
                        })
                        .slice(0, 5)
                        .map(([tool, level]) => (
                          <span
                            key={tool}
                            className={cn(
                              "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium",
                              proficiencyStyles[level] ?? "bg-secondary text-secondary-foreground",
                            )}
                          >
                            {tool}
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
