import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { TeamSkillGap } from "@/types/api"

interface TeamSkillGapsProps {
  data: TeamSkillGap[]
}

export function TeamSkillGaps({ data }: TeamSkillGapsProps) {
  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Team Skill Gaps</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No significant skill gaps detected. All skills have good team coverage.
          </p>
        </CardContent>
      </Card>
    )
  }

  const sorted = [...data].sort((a, b) => a.coverage_pct - b.coverage_pct)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Team Skill Gaps</CardTitle>
        <p className="text-xs text-muted-foreground">Skills with &lt;30% team coverage</p>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {sorted.map((gap) => (
            <div key={gap.skill} className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">{gap.skill}</span>
                <span className="text-muted-foreground">
                  {gap.engineers_with_skill}/{gap.total_engineers} engineers ({gap.coverage_pct.toFixed(0)}%)
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className={cn(
                    "h-full rounded-full transition-all",
                    gap.coverage_pct < 15
                      ? "bg-destructive"
                      : "bg-amber-500 dark:bg-amber-400",
                  )}
                  style={{ width: `${Math.max(gap.coverage_pct, 2)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
