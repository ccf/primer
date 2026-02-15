import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface SkillUniverseChartProps {
  universe: Record<string, number>
}

export function SkillUniverseChart({ universe }: SkillUniverseChartProps) {
  const entries = Object.entries(universe).sort(([, a], [, b]) => b - a)
  const maxCount = entries.length > 0 ? entries[0][1] : 1

  if (entries.length === 0) {
    return null
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Team Skill Universe</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {entries.slice(0, 20).map(([skill, count]) => (
            <div key={skill} className="flex items-center gap-3">
              <span className="w-32 truncate text-sm">{skill}</span>
              <div className="flex-1">
                <div className="h-5 rounded bg-secondary">
                  <div
                    className="flex h-5 items-center rounded bg-primary/20 px-2 text-xs font-medium"
                    style={{ width: `${Math.max((count / maxCount) * 100, 8)}%` }}
                  >
                    {count}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
