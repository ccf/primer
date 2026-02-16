import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
  Legend,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { CardSkeleton } from "@/components/shared/loading-skeleton"
import { useTimeToTeamAverage } from "@/hooks/use-api-queries"
import { cn, formatPercent } from "@/lib/utils"
import { TrendingUp, Users } from "lucide-react"

interface TimeToTeamAverageProps {
  teamId: string | null
  startDate?: string
  endDate?: string
}

const CHART_COLORS = [
  "#6366f1",
  "#22c55e",
  "#f59e0b",
  "#ec4899",
  "#06b6d4",
  "#8b5cf6",
  "#f97316",
  "#14b8a6",
]

export function TimeToTeamAverage({ teamId, startDate, endDate }: TimeToTeamAverageProps) {
  const { data, isLoading } = useTimeToTeamAverage(teamId, startDate, endDate)

  if (isLoading) {
    return <CardSkeleton />
  }

  if (!data || data.total_engineers === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Time to Team Average</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="py-8 text-center text-sm text-muted-foreground">
            No rampup data available yet.
          </p>
        </CardContent>
      </Card>
    )
  }

  // Build chart data: pivot engineer weekly rates into columns keyed by week_number
  const weekNumbers = new Set<number>()
  for (const eng of data.engineers) {
    for (const pt of eng.weekly_success_rates) {
      weekNumbers.add(pt.week_number)
    }
  }
  const sortedWeeks = [...weekNumbers].sort((a, b) => a - b)

  const chartData = sortedWeeks.map((week) => {
    const point: Record<string, number | null> = { week }
    for (const eng of data.engineers) {
      const match = eng.weekly_success_rates.find((pt) => pt.week_number === week)
      point[eng.name] = match?.success_rate != null ? match.success_rate * 100 : null
    }
    return point
  })

  return (
    <div className="space-y-4">
      {/* Headline stat */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <div className="rounded-lg bg-primary/10 p-2">
                <TrendingUp className="h-4 w-4 text-primary" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Avg Weeks to Match</p>
                <p className="text-xl font-bold">
                  {data.avg_weeks_to_match != null ? `${data.avg_weeks_to_match.toFixed(1)}w` : "-"}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <div className="rounded-lg bg-primary/10 p-2">
                <Users className="h-4 w-4 text-primary" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Matched Team Avg</p>
                <p className="text-xl font-bold">
                  {data.engineers_who_matched} / {data.total_engineers}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <div className="rounded-lg bg-primary/10 p-2">
                <TrendingUp className="h-4 w-4 text-primary" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Team Avg Success</p>
                <p className="text-xl font-bold">
                  {formatPercent(data.team_avg_success_rate)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Line chart */}
      {chartData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">
              Success Rate Rampup by Week
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis
                  dataKey="week"
                  tick={{ fontSize: 11 }}
                  label={{ value: "Week", position: "insideBottomRight", offset: -5, fontSize: 11 }}
                />
                <YAxis
                  tick={{ fontSize: 11 }}
                  domain={[0, 100]}
                  label={{ value: "Success %", angle: -90, position: "insideLeft", fontSize: 11 }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "8px",
                    fontSize: "12px",
                  }}
                  formatter={(value) => [`${(value as number).toFixed(0)}%`]}
                  labelFormatter={(label) => `Week ${label}`}
                />
                <Legend />
                <ReferenceLine
                  y={data.team_avg_success_rate * 100}
                  stroke="hsl(var(--muted-foreground))"
                  strokeDasharray="6 3"
                  label={{
                    value: `Team avg (${(data.team_avg_success_rate * 100).toFixed(0)}%)`,
                    position: "right",
                    fontSize: 10,
                    fill: "hsl(var(--muted-foreground))",
                  }}
                />
                {data.engineers.slice(0, 8).map((eng, i) => (
                  <Line
                    key={eng.engineer_id}
                    type="monotone"
                    dataKey={eng.name}
                    stroke={CHART_COLORS[i % CHART_COLORS.length]}
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Engineer table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Engineer Rampup Details</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs text-muted-foreground">
                  <th className="pb-2 pr-4">Engineer</th>
                  <th className="pb-2 pr-4">First Session</th>
                  <th className="pb-2 pr-4">Weeks to Match</th>
                  <th className="pb-2 pr-4">Current Rate</th>
                  <th className="pb-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {data.engineers.map((eng) => {
                  const matched = eng.weeks_to_team_average != null
                  const currentRate = eng.current_success_rate
                  const aboveAvg = currentRate != null && currentRate >= data.team_avg_success_rate
                  return (
                    <tr key={eng.engineer_id} className="border-b border-border last:border-0">
                      <td className="py-2 pr-4 font-medium">{eng.name}</td>
                      <td className="py-2 pr-4 text-muted-foreground">
                        {eng.first_session_date}
                      </td>
                      <td className="py-2 pr-4">
                        {matched ? `${eng.weeks_to_team_average}w` : "-"}
                      </td>
                      <td className="py-2 pr-4">{formatPercent(currentRate)}</td>
                      <td className="py-2">
                        <Badge
                          variant={aboveAvg ? "success" : matched ? "warning" : "secondary"}
                          className={cn("text-[10px]")}
                        >
                          {aboveAvg ? "Above avg" : matched ? "Matched" : "Ramping"}
                        </Badge>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
