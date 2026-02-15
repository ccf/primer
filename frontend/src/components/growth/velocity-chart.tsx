import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { NewHireProgress } from "@/types/api"

interface VelocityChartProps {
  progress: NewHireProgress[]
}

export function VelocityChart({ progress }: VelocityChartProps) {
  if (progress.length === 0) {
    return null
  }

  const sorted = [...progress].sort((a, b) => b.velocity_score - a.velocity_score)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Velocity Scores</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {sorted.map((nhp) => (
            <div key={nhp.engineer_id} className="flex items-center gap-3">
              <span className="w-28 truncate text-sm">{nhp.name}</span>
              <div className="flex-1">
                <div className="h-6 rounded bg-secondary">
                  <div
                    className={cn(
                      "flex h-6 items-center rounded px-2 text-xs font-medium text-white",
                      nhp.velocity_score >= 70
                        ? "bg-success"
                        : nhp.velocity_score >= 40
                          ? "bg-warning"
                          : "bg-destructive",
                    )}
                    style={{ width: `${Math.max(nhp.velocity_score, 5)}%` }}
                  >
                    {nhp.velocity_score.toFixed(0)}
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
