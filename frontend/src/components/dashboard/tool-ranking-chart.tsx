import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartTooltip } from "@/components/charts/chart-tooltip"
import { CHART_COLORS, AXIS_TICK_STYLE } from "@/lib/chart-colors"
import type { ToolRanking } from "@/types/api"

interface ToolRankingChartProps {
  data: ToolRanking[]
}

export function ToolRankingChart({ data }: ToolRankingChartProps) {
  const chartData = data.slice(0, 10).map((t) => ({
    name: t.tool_name,
    calls: t.total_calls,
  }))

  if (chartData.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Top Tools</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={chartData} layout="vertical">
            <XAxis type="number" tick={AXIS_TICK_STYLE} />
            <YAxis dataKey="name" type="category" width={80} tick={AXIS_TICK_STYLE} />
            <Tooltip content={<ChartTooltip />} />
            <Bar dataKey="calls" fill={CHART_COLORS.quaternary} radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
