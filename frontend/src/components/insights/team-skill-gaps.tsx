import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn, formatLabel } from "@/lib/utils"
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
                <div className="space-y-1">
                  <span className="font-medium">{gap.skill}</span>
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="outline">{formatLabel(gap.gap_type)}</Badge>
                    {gap.workflow_archetype && (
                      <Badge variant="outline">{formatLabel(gap.workflow_archetype)}</Badge>
                    )}
                    {gap.tool_category && (
                      <Badge variant="outline">{formatLabel(gap.tool_category)}</Badge>
                    )}
                    {gap.project_context && (
                      <Badge variant="outline">{gap.project_context}</Badge>
                    )}
                    {gap.recommended_identifier && (
                      <Badge variant="secondary">
                        {gap.recommended_asset_type
                          ? `${formatLabel(gap.recommended_asset_type)}: ${gap.recommended_identifier}`
                          : gap.recommended_identifier}
                      </Badge>
                    )}
                  </div>
                </div>
                <span className="text-muted-foreground">
                  {gap.engineers_with_skill}/{gap.total_engineers} engineers ({gap.coverage_pct.toFixed(0)}%)
                </span>
              </div>
              {gap.evidence_summary && (
                <p className="text-xs text-muted-foreground">{gap.evidence_summary}</p>
              )}
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
