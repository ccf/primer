import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartTooltip } from "@/components/charts/chart-tooltip"
import { CHART_COLORS, AXIS_TICK_STYLE } from "@/lib/chart-colors"
import type { ModelRanking } from "@/types/api"
import { formatTokens } from "@/lib/utils"

interface ModelUsageChartProps {
  data: ModelRanking[]
}

export function ModelUsageChart({ data }: ModelUsageChartProps) {
  const chartData = data.map((m) => ({
    name: m.model_name.replace(/^claude-/, "").split("-202")[0],
    input: m.total_input_tokens,
    output: m.total_output_tokens,
  }))

  if (chartData.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Model Usage (tokens)</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={chartData}>
            <XAxis dataKey="name" tick={AXIS_TICK_STYLE} />
            <YAxis tickFormatter={(v) => formatTokens(v as number)} tick={AXIS_TICK_STYLE} />
            <Tooltip content={<ChartTooltip formatter={(v) => formatTokens(v)} />} />
            <Legend />
            <Bar dataKey="input" fill={CHART_COLORS.primary} stackId="a" radius={[0, 0, 0, 0]} />
            <Bar dataKey="output" fill={CHART_COLORS.quaternary} stackId="a" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
