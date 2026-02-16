import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { SkillInventoryResponse, EngineerLearningPath } from "@/types/api"

interface StrengthsTabProps {
  strengths: SkillInventoryResponse
  learningPaths: EngineerLearningPath[]
}

const proficiencyColor: Record<string, string> = {
  expert: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400",
  proficient: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
  moderate: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400",
  novice: "bg-gray-100 text-gray-600 dark:bg-gray-800/50 dark:text-gray-400",
}

const priorityVariant: Record<string, "destructive" | "warning" | "secondary"> = {
  high: "destructive",
  medium: "warning",
  low: "secondary",
}

export function StrengthsTab({ strengths, learningPaths }: StrengthsTabProps) {
  const profiles = strengths.engineer_profiles
  const hasProfiles = profiles.length > 0
  const hasLearning = learningPaths.length > 0

  if (!hasProfiles && !hasLearning) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">
        No skill profile data available yet.
      </div>
    )
  }

  // Aggregate tool proficiency from all profiles (for single engineer, there's typically 1)
  const toolProficiency: Record<string, string> = {}
  for (const profile of profiles) {
    for (const [tool, level] of Object.entries(profile.tool_proficiency)) {
      toolProficiency[tool] = level
    }
  }

  // Gather all recommendations from learning paths
  const allRecommendations = learningPaths.flatMap((lp) => lp.recommendations)

  return (
    <div className="space-y-6">
      {Object.keys(toolProficiency).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Tool Proficiency</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {Object.entries(toolProficiency)
                .sort(([, a], [, b]) => {
                  const order = ["expert", "proficient", "moderate", "novice"]
                  return order.indexOf(a) - order.indexOf(b)
                })
                .map(([tool, level]) => (
                  <span
                    key={tool}
                    className={cn(
                      "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium",
                      proficiencyColor[level] ?? proficiencyColor.novice,
                    )}
                  >
                    {tool}
                    <span className="opacity-60">{level}</span>
                  </span>
                ))}
            </div>
          </CardContent>
        </Card>
      )}

      {profiles.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-3">
          <Card>
            <CardContent className="p-4">
              <p className="text-xs text-muted-foreground">Projects</p>
              <p className="mt-1 text-2xl font-bold">{profiles[0].project_count}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <p className="text-xs text-muted-foreground">Total Sessions</p>
              <p className="mt-1 text-2xl font-bold">{profiles[0].total_sessions}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <p className="text-xs text-muted-foreground">Diversity Score</p>
              <p className="mt-1 text-2xl font-bold">{profiles[0].diversity_score.toFixed(1)}</p>
            </CardContent>
          </Card>
        </div>
      )}

      {profiles.length > 0 && Object.keys(profiles[0].session_types).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Session Types</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {Object.entries(profiles[0].session_types)
                .sort(([, a], [, b]) => b - a)
                .map(([type, count]) => (
                  <Badge key={type} variant="secondary">
                    {type.replace(/_/g, " ")} ({count})
                  </Badge>
                ))}
            </div>
          </CardContent>
        </Card>
      )}

      {allRecommendations.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-medium">Learning Recommendations</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            {allRecommendations.map((rec, i) => (
              <Card key={i}>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-2">
                    <div className="space-y-1">
                      <p className="text-sm font-medium">{rec.title}</p>
                      <p className="text-xs text-muted-foreground">{rec.description}</p>
                      <p className="text-xs text-muted-foreground">
                        Skill area: {rec.skill_area.replace(/_/g, " ")}
                      </p>
                    </div>
                    <Badge variant={priorityVariant[rec.priority] ?? "secondary"}>
                      {rec.priority}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
