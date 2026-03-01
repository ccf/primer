import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartTooltip } from "@/components/charts/chart-tooltip"
import { CHART_COLORS, AXIS_TICK_STYLE } from "@/lib/chart-colors"

interface SessionTypeChartProps {
  data: Record<string, number>
}

export function SessionTypeChart({ data }: SessionTypeChartProps) {
  const chartData = Object.entries(data)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)

  if (chartData.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Session Types</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={chartData}>
            <XAxis dataKey="name" tick={AXIS_TICK_STYLE} />
            <YAxis allowDecimals={false} tick={AXIS_TICK_STYLE} />
            <Tooltip content={<ChartTooltip />} />
            <Bar dataKey="count" fill={CHART_COLORS.primary} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
