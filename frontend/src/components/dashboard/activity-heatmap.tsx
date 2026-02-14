import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { ActivityHeatmap as ActivityHeatmapData } from "@/types/api"

interface ActivityHeatmapProps {
  data: ActivityHeatmapData
}

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
const HOURS = Array.from({ length: 24 }, (_, i) => i)

function getIntensity(count: number, maxCount: number): string {
  if (count === 0 || maxCount === 0) return "bg-muted/30"
  const ratio = count / maxCount
  if (ratio > 0.75) return "bg-primary"
  if (ratio > 0.5) return "bg-primary/75"
  if (ratio > 0.25) return "bg-primary/50"
  return "bg-primary/25"
}

export function ActivityHeatmap({ data }: ActivityHeatmapProps) {
  const grid = new Map<string, number>()
  for (const cell of data.cells) {
    grid.set(`${cell.day_of_week}-${cell.hour}`, cell.count)
  }

  return (
    <Card className="col-span-full">
      <CardHeader>
        <CardTitle className="text-sm font-medium">Activity Heatmap</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <div className="min-w-[600px]">
            {/* Hour labels */}
            <div className="mb-1 flex">
              <div className="w-10" />
              {HOURS.map((h) => (
                <div key={h} className="flex-1 text-center text-[10px] text-muted-foreground">
                  {h % 3 === 0 ? `${h}` : ""}
                </div>
              ))}
            </div>
            {/* Grid rows */}
            {DAYS.map((day, dayIdx) => (
              <div key={day} className="mb-0.5 flex items-center">
                <div className="w-10 text-xs text-muted-foreground">{day}</div>
                <div className="flex flex-1 gap-0.5">
                  {HOURS.map((hour) => {
                    const count = grid.get(`${dayIdx}-${hour}`) ?? 0
                    return (
                      <div
                        key={hour}
                        className={cn(
                          "aspect-square flex-1 rounded-sm transition-colors",
                          getIntensity(count, data.max_count),
                        )}
                        title={`${day} ${hour}:00 — ${count} session${count !== 1 ? "s" : ""}`}
                      />
                    )
                  })}
                </div>
              </div>
            ))}
            {/* Legend */}
            <div className="mt-3 flex items-center justify-end gap-1 text-[10px] text-muted-foreground">
              <span>Less</span>
              <div className="h-3 w-3 rounded-sm bg-muted/30" />
              <div className="h-3 w-3 rounded-sm bg-primary/25" />
              <div className="h-3 w-3 rounded-sm bg-primary/50" />
              <div className="h-3 w-3 rounded-sm bg-primary/75" />
              <div className="h-3 w-3 rounded-sm bg-primary" />
              <span>More</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
