import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { OnboardingRecommendation } from "@/types/api"

const categoryColors: Record<string, string> = {
  tool_adoption: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  complexity: "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400",
  mentoring: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
  friction: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
}

interface OnboardingRecommendationsProps {
  recommendations: OnboardingRecommendation[]
}

export function OnboardingRecommendations({ recommendations }: OnboardingRecommendationsProps) {
  if (recommendations.length === 0) {
    return null
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium text-muted-foreground">
        {recommendations.length} recommendation{recommendations.length !== 1 ? "s" : ""}
      </h3>
      {recommendations.map((rec, i) => (
        <Card key={i}>
          <CardContent className="p-4">
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={cn(
                  "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
                  categoryColors[rec.category] ?? "bg-secondary text-secondary-foreground",
                )}
              >
                {rec.category.replace(/_/g, " ")}
              </span>
              {rec.target_engineer_id && (
                <Badge variant="outline">individual</Badge>
              )}
            </div>
            <h3 className="mt-2 font-medium">{rec.title}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{rec.description}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
