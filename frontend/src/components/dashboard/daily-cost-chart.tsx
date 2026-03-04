import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartTooltip } from "@/components/charts/chart-tooltip"
import { CHART_COLORS, AXIS_TICK_STYLE } from "@/lib/chart-colors"
import type { DailyCostEntry } from "@/types/api"
import { format, parseISO } from "date-fns"
import { formatCost } from "@/lib/utils"

interface DailyCostChartProps {
  data: DailyCostEntry[]
}

export function DailyCostChart({ data }: DailyCostChartProps) {
  const chartData = [...data]
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((d) => ({
      date: format(parseISO(d.date), "MMM d"),
      cost: d.estimated_cost,
    }))

  if (chartData.length === 0) return null

  return (
    <Card className="min-w-0">
      <CardHeader>
        <CardTitle className="text-sm font-medium">Daily Estimated Cost</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="colorCost" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={CHART_COLORS.tertiary} stopOpacity={0.2} />
                <stop offset="95%" stopColor={CHART_COLORS.tertiary} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis dataKey="date" tick={AXIS_TICK_STYLE} />
            <YAxis tickFormatter={(v) => formatCost(v as number)} tick={AXIS_TICK_STYLE} />
            <Tooltip content={<ChartTooltip formatter={(v) => formatCost(v)} />} />
            <Area
              type="monotone"
              dataKey="cost"
              stroke={CHART_COLORS.tertiary}
              fill="url(#colorCost)"
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
