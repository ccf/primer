import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { ConfigSuggestion } from "@/types/api"

const categoryColors: Record<string, string> = {
  hook: "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400",
  permission: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  model: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  mcp: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
  workflow: "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400",
}

interface ConfigSuggestionsListProps {
  suggestions: ConfigSuggestion[]
  sessionsAnalyzed: number
}

export function ConfigSuggestionsList({ suggestions, sessionsAnalyzed }: ConfigSuggestionsListProps) {
  if (suggestions.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">
        No config suggestions based on {sessionsAnalyzed} sessions analyzed.
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        {suggestions.length} suggestion{suggestions.length !== 1 ? "s" : ""} from {sessionsAnalyzed} sessions
      </p>
      {suggestions.map((s, i) => (
        <Card key={i}>
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={cn(
                    "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
                    categoryColors[s.category] ?? "bg-secondary text-secondary-foreground",
                  )}
                >
                  {s.category}
                </span>
                <Badge variant={s.severity === "warning" ? "warning" : "outline"}>
                  {s.severity}
                </Badge>
              </div>
            </div>
            <h3 className="mt-2 font-medium">{s.title}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{s.description}</p>
            {s.suggested_config && (
              <pre className="mt-3 overflow-x-auto rounded-lg bg-muted p-3 text-xs">
                {s.suggested_config}
              </pre>
            )}
            {Object.keys(s.evidence).length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {Object.entries(s.evidence).map(([key, val]) => (
                  <span key={key} className="text-xs text-muted-foreground">
                    {key}: <span className="font-medium text-foreground">{String(val)}</span>
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
