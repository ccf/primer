import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { EngineerLearningPath } from "@/types/api"

const categoryColors: Record<string, string> = {
  session_type_gap: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  tool_gap: "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400",
  complexity: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  goal_gap: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
}

const trendArrow: Record<string, string> = {
  increasing: "↑",
  flat: "→",
  decreasing: "↓",
}

interface LearningPathCardsProps {
  paths: EngineerLearningPath[]
}

export function LearningPathCards({ paths }: LearningPathCardsProps) {
  if (paths.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">
        No learning paths available.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {paths.map((path) => (
        <Card key={path.engineer_id}>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">{path.name}</CardTitle>
              <div className="flex items-center gap-3">
                <span className="text-sm text-muted-foreground">
                  Complexity {trendArrow[path.complexity_trend] ?? "→"}{" "}
                  <span className="capitalize">{path.complexity_trend}</span>
                </span>
                <span className="text-sm text-muted-foreground">
                  {path.total_sessions} sessions
                </span>
              </div>
            </div>
            <div className="mt-2">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>Coverage</span>
                <span>{(path.coverage_score * 100).toFixed(0)}%</span>
              </div>
              <div className="mt-1 h-2 rounded-full bg-secondary">
                <div
                  className={cn(
                    "h-2 rounded-full",
                    path.coverage_score >= 0.7 ? "bg-success" : path.coverage_score >= 0.4 ? "bg-warning" : "bg-destructive",
                  )}
                  style={{ width: `${path.coverage_score * 100}%` }}
                />
              </div>
            </div>
          </CardHeader>
          {path.recommendations.length > 0 && (
            <CardContent className="space-y-2">
              {path.recommendations.map((rec, i) => (
                <div key={i} className="flex items-start gap-2 rounded-lg border border-border p-3">
                  <span
                    className={cn(
                      "mt-0.5 inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-xs font-medium",
                      categoryColors[rec.category] ?? "bg-secondary text-secondary-foreground",
                    )}
                  >
                    {rec.category.replace(/_/g, " ")}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{rec.title}</span>
                      <Badge variant={rec.priority === "high" ? "warning" : "outline"}>
                        {rec.priority}
                      </Badge>
                    </div>
                    <p className="mt-0.5 text-xs text-muted-foreground">{rec.description}</p>
                  </div>
                </div>
              ))}
            </CardContent>
          )}
        </Card>
      ))}
    </div>
  )
}
