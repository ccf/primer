import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { PersonalizedTip } from "@/types/api"

const categoryColors: Record<string, string> = {
  tool_gap: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  diversity: "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400",
  friction: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  success: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  workflow: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
}

interface PersonalizedTipsListProps {
  tips: PersonalizedTip[]
  sessionsAnalyzed: number
}

export function PersonalizedTipsList({ tips, sessionsAnalyzed }: PersonalizedTipsListProps) {
  if (tips.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">
        No personalized tips based on {sessionsAnalyzed} sessions analyzed.
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        {tips.length} tip{tips.length !== 1 ? "s" : ""} from {sessionsAnalyzed} sessions
      </p>
      {tips.map((tip, i) => (
        <Card key={i}>
          <CardContent className="p-4">
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={cn(
                  "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
                  categoryColors[tip.category] ?? "bg-secondary text-secondary-foreground",
                )}
              >
                {tip.category.replace("_", " ")}
              </span>
              <Badge variant={tip.severity === "warning" ? "warning" : "outline"}>
                {tip.severity}
              </Badge>
            </div>
            <h3 className="mt-2 font-medium">{tip.title}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{tip.description}</p>
            {Object.keys(tip.evidence).length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {Object.entries(tip.evidence).map(([key, val]) => (
                  <span key={key} className="text-xs text-muted-foreground">
                    {key}: <span className="font-medium text-foreground">{Array.isArray(val) ? val.join(", ") : String(val)}</span>
                  </span>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
