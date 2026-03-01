import {
  AreaChart,
  Area,
  ResponsiveContainer,
  Tooltip,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatCost, formatDuration, formatPercent } from "@/lib/utils"
import type { WeeklyMetricPoint } from "@/types/api"

interface TrajectorySparklineProps {
  data: WeeklyMetricPoint[]
}

interface SparklineCardProps {
  title: string
  data: { week: string; value: number | null }[]
  formatter: (value: number) => string
  gradientId: string
}

function SparklineCard({ title, data, formatter, gradientId }: SparklineCardProps) {
  const filtered = data.filter((d) => d.value != null)

  if (filtered.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-xs font-medium text-muted-foreground">{title}</CardTitle>
        </CardHeader>
        <CardContent className="pb-4">
          <p className="text-sm text-muted-foreground">No data</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-xs font-medium text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent className="pb-4">
        <ResponsiveContainer width="100%" height={80}>
          <AreaChart data={filtered}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--color-primary)" stopOpacity={0.35} />
                <stop offset="95%" stopColor="var(--color-primary)" stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <Tooltip
              contentStyle={{
                backgroundColor: "var(--color-card)",
                border: "1px solid var(--color-border)",
                borderRadius: "8px",
                fontSize: "12px",
              }}
              labelFormatter={(label) => `Week of ${label}`}
              formatter={(value) => [formatter(value as number), title]}
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke="var(--color-primary)"
              fill={`url(#${gradientId})`}
              strokeWidth={2}
              dot={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}

export function TrajectorySparklines({ data }: TrajectorySparklineProps) {
  const sessionsData = data.map((d) => ({ week: d.week, value: d.session_count }))
  const successData = data.map((d) => ({ week: d.week, value: d.success_rate }))
  const costData = data.map((d) => ({ week: d.week, value: d.estimated_cost }))
  const durationData = data.map((d) => ({ week: d.week, value: d.avg_duration }))

  const cards = [
    { title: "Sessions", data: sessionsData, formatter: (v: number) => String(v), gradientId: "sparkSessions" },
    { title: "Success Rate", data: successData, formatter: (v: number) => formatPercent(v), gradientId: "sparkSuccess" },
    { title: "Cost", data: costData, formatter: (v: number) => formatCost(v), gradientId: "sparkCost" },
    { title: "Avg Duration", data: durationData, formatter: (v: number) => formatDuration(v), gradientId: "sparkDuration" },
  ]

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((c, i) => (
        <div
          key={c.gradientId}
          className="animate-stagger-in"
          style={{ animationDelay: `${i * 60}ms` }}
        >
          <SparklineCard
            title={c.title}
            data={c.data}
            formatter={c.formatter}
            gradientId={c.gradientId}
          />
        </div>
      ))}
    </div>
  )
}
