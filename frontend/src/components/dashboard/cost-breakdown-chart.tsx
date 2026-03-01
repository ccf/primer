import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartTooltip } from "@/components/charts/chart-tooltip"
import { CHART_COLORS, AXIS_TICK_STYLE } from "@/lib/chart-colors"
import type { ModelCostBreakdown } from "@/types/api"
import { formatCost } from "@/lib/utils"

interface CostBreakdownChartProps {
  data: ModelCostBreakdown[]
}

export function CostBreakdownChart({ data }: CostBreakdownChartProps) {
  const chartData = data.map((m) => ({
    name: m.model_name.replace(/^claude-/, "").split("-202")[0],
    cost: m.estimated_cost,
  }))

  if (chartData.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Cost by Model</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={chartData}>
            <XAxis dataKey="name" tick={AXIS_TICK_STYLE} />
            <YAxis tickFormatter={(v) => formatCost(v as number)} tick={AXIS_TICK_STYLE} />
            <Tooltip content={<ChartTooltip formatter={(v) => formatCost(v)} />} />
            <Legend />
            <Bar dataKey="cost" fill={CHART_COLORS.tertiary} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
