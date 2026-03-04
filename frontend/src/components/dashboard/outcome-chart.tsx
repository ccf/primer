import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartTooltip } from "@/components/charts/chart-tooltip"
import { CHART_PALETTE } from "@/lib/chart-colors"

interface OutcomeChartProps {
  data: Record<string, number>
}

export function OutcomeChart({ data }: OutcomeChartProps) {
  const chartData = Object.entries(data).map(([name, value]) => ({ name, value }))

  if (chartData.length === 0) return null

  const total = chartData.reduce((s, d) => s + d.value, 0)

  // Filter out entries that round to 0% for cleaner legend
  const nonZero = chartData.filter((d) => d.value > 0 && (total > 0 ? Math.round((d.value / total) * 100) : 0) > 0)

  return (
    <Card className="flex flex-col">
      <CardHeader className="pb-1">
        <CardTitle className="text-sm font-medium">Outcomes</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col justify-center gap-2 pt-0">
        <ResponsiveContainer width="100%" height={140}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={35}
              outerRadius={58}
              paddingAngle={2}
              dataKey="value"
              strokeWidth={0}
            >
              {chartData.map((_, i) => (
                <Cell key={i} fill={CHART_PALETTE[i % CHART_PALETTE.length]} />
              ))}
            </Pie>
            <Tooltip content={<ChartTooltip />} />
          </PieChart>
        </ResponsiveContainer>
        <div className="grid grid-cols-2 gap-x-2 gap-y-0.5">
          {nonZero.map((d) => {
            const origIdx = chartData.findIndex((c) => c.name === d.name)
            return (
              <div key={d.name} className="flex items-center gap-1.5">
                <span
                  className="inline-block h-1.5 w-1.5 shrink-0 rounded-full"
                  style={{ backgroundColor: CHART_PALETTE[origIdx % CHART_PALETTE.length] }}
                />
                <span className="truncate text-[10px] text-muted-foreground">
                  {d.name}{" "}
                  <span className="font-medium text-foreground">
                    {total > 0 ? Math.round((d.value / total) * 100) : 0}%
                  </span>
                </span>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
