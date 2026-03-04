import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartTooltip } from "@/components/charts/chart-tooltip"
import { CHART_COLORS, AXIS_TICK_STYLE } from "@/lib/chart-colors"
import type { DailyStatsResponse } from "@/types/api"
import { format, parseISO } from "date-fns"

interface DailyActivityChartProps {
  data: DailyStatsResponse[]
}

export function DailyActivityChart({ data }: DailyActivityChartProps) {
  const chartData = [...data]
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((d) => ({
      date: format(parseISO(d.date), "MMM d"),
      sessions: d.session_count,
      messages: d.message_count,
    }))

  return (
    <Card className="min-w-0">
      <CardHeader>
        <CardTitle className="text-sm font-medium">Daily Activity</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="colorSessions" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={CHART_COLORS.primary} stopOpacity={0.2} />
                <stop offset="95%" stopColor={CHART_COLORS.primary} stopOpacity={0} />
              </linearGradient>
              <linearGradient id="colorMessages" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={CHART_COLORS.secondary} stopOpacity={0.2} />
                <stop offset="95%" stopColor={CHART_COLORS.secondary} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis dataKey="date" tick={AXIS_TICK_STYLE} />
            <YAxis allowDecimals={false} tick={AXIS_TICK_STYLE} />
            <Tooltip content={<ChartTooltip />} />
            <Area
              type="monotone"
              dataKey="sessions"
              stroke={CHART_COLORS.primary}
              fill="url(#colorSessions)"
              strokeWidth={2}
            />
            <Area
              type="monotone"
              dataKey="messages"
              stroke={CHART_COLORS.secondary}
              fill="url(#colorMessages)"
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
