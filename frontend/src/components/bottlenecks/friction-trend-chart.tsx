import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { FrictionTrend } from "@/types/api"
import { format, parseISO } from "date-fns"

interface FrictionTrendChartProps {
  data: FrictionTrend[]
}

export function FrictionTrendChart({ data }: FrictionTrendChartProps) {
  const chartData = [...data]
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((d) => ({
      date: format(parseISO(d.date), "MMM d"),
      frictionCount: d.total_friction_count,
      frictionRate:
        d.total_sessions > 0
          ? Math.round((d.sessions_with_friction / d.total_sessions) * 100)
          : 0,
    }))

  if (chartData.length === 0) return null

  return (
    <Card className="col-span-full">
      <CardHeader>
        <CardTitle className="text-sm font-medium">Friction Trends</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={chartData}>
            <defs>
              <linearGradient id="colorFriction" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} />
            <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
            <YAxis
              yAxisId="right"
              orientation="right"
              tick={{ fontSize: 11 }}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip
              formatter={(value, name) =>
                name === "frictionRate" ? `${value}%` : value
              }
            />
            <Legend />
            <Area
              yAxisId="left"
              type="monotone"
              dataKey="frictionCount"
              name="Friction Count"
              stroke="#f59e0b"
              fill="url(#colorFriction)"
              strokeWidth={2}
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="frictionRate"
              name="Friction Rate %"
              stroke="#6366f1"
              strokeWidth={2}
              dot={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
