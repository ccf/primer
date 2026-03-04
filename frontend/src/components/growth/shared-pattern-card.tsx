import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"
import type { SharedPattern } from "@/types/api"

const typeColors: Record<string, string> = {
  session_type: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  goal_category: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
  project: "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400",
}

function formatDuration(seconds: number | null): string {
  if (seconds == null) return "—"
  if (seconds < 60) return `${Math.round(seconds)}s`
  return `${(seconds / 60).toFixed(1)}m`
}

interface SharedPatternCardProps {
  patterns: SharedPattern[]
}

export function SharedPatternCards({ patterns }: SharedPatternCardProps) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  if (patterns.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">
        No shared patterns found. Patterns emerge when multiple engineers work on similar tasks.
      </div>
    )
  }

  function toggle(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  return (
    <div className="space-y-2">
      {patterns.map((pattern) => {
        const isOpen = expanded.has(pattern.cluster_id)
        return (
          <Card key={pattern.cluster_id}>
            <CardHeader
              className="cursor-pointer select-none pb-3 transition-colors hover:bg-accent/50"
              onClick={() => toggle(pattern.cluster_id)}
            >
              <div className="flex items-center gap-2">
                <ChevronRight
                  className={cn(
                    "h-4 w-4 shrink-0 text-muted-foreground transition-transform",
                    isOpen && "rotate-90",
                  )}
                />
                <span
                  className={cn(
                    "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
                    typeColors[pattern.cluster_type] ?? "bg-secondary text-secondary-foreground",
                  )}
                >
                  {pattern.cluster_type.replace(/_/g, " ")}
                </span>
                <CardTitle className="text-base">{pattern.cluster_label}</CardTitle>
              </div>
              <p className="mt-1 pl-6 text-sm text-muted-foreground">{pattern.insight}</p>
              <div className="mt-2 flex gap-4 pl-6 text-xs text-muted-foreground">
                <span>{pattern.engineer_count} engineers</span>
                <span>{pattern.session_count} sessions</span>
                {pattern.avg_duration != null && <span>Avg {formatDuration(pattern.avg_duration)}</span>}
                {pattern.success_rate != null && <span>{(pattern.success_rate * 100).toFixed(0)}% success</span>}
              </div>
            </CardHeader>
            {isOpen && (
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border text-left text-xs text-muted-foreground">
                        <th className="pb-2 pr-4">Engineer</th>
                        <th className="pb-2 pr-4">Duration</th>
                        <th className="pb-2 pr-4">Tools</th>
                        <th className="pb-2 pr-4">Outcome</th>
                      </tr>
                    </thead>
                    <tbody>
                      {pattern.approaches.map((a) => {
                        const isBest = pattern.best_approach?.session_id === a.session_id
                        return (
                          <tr
                            key={a.session_id}
                            className={cn("border-b border-border last:border-0", isBest && "bg-success/5")}
                          >
                            <td className="py-2 pr-4">
                              {a.name}
                              {isBest && (
                                <Badge variant="success" className="ml-2">
                                  best
                                </Badge>
                              )}
                            </td>
                            <td className="py-2 pr-4">{formatDuration(a.duration_seconds)}</td>
                            <td className="py-2 pr-4">
                              <span className="text-xs text-muted-foreground">{a.tools_used.join(", ") || "—"}</span>
                            </td>
                            <td className="py-2 pr-4">
                              {a.outcome ? (
                                <Badge variant={a.outcome === "success" ? "success" : "outline"}>{a.outcome}</Badge>
                              ) : (
                                "—"
                              )}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            )}
          </Card>
        )
      })}
    </div>
  )
}
