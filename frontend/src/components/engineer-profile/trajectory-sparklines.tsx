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
                <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
              </linearGradient>
            </defs>
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "8px",
                fontSize: "12px",
              }}
              labelFormatter={(label) => `Week of ${label}`}
              formatter={(value) => [formatter(value as number), title]}
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke="hsl(var(--primary))"
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

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <SparklineCard
        title="Sessions"
        data={sessionsData}
        formatter={(v) => String(v)}
        gradientId="sparkSessions"
      />
      <SparklineCard
        title="Success Rate"
        data={successData}
        formatter={(v) => formatPercent(v)}
        gradientId="sparkSuccess"
      />
      <SparklineCard
        title="Cost"
        data={costData}
        formatter={(v) => formatCost(v)}
        gradientId="sparkCost"
      />
      <SparklineCard
        title="Avg Duration"
        data={durationData}
        formatter={(v) => formatDuration(v)}
        gradientId="sparkDuration"
      />
    </div>
  )
}
