import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartTooltip } from "@/components/charts/chart-tooltip"
import { CHART_COLORS, AXIS_TICK_STYLE } from "@/lib/chart-colors"
import { useCostForecast } from "@/hooks/use-api-queries"
import { CardSkeleton, ChartSkeleton } from "@/components/shared/loading-skeleton"
import { formatCost, cn } from "@/lib/utils"
import { format, parseISO } from "date-fns"

interface ForecastTabProps {
  teamId: string | null
  startDate?: string
  endDate?: string
}

interface ChartPoint {
  date: string
  cost?: number
  projected_cost?: number
  upper_bound?: number
  lower_bound?: number
}

export function ForecastTab({ teamId, startDate, endDate }: ForecastTabProps) {
  const { data, isLoading } = useCostForecast(teamId, startDate, endDate)

  if (isLoading) {
    return (
      <div className="space-y-4">
        <CardSkeleton />
        <ChartSkeleton />
      </div>
    )
  }

  if (!data) return null

  const trendBadge = (() => {
    switch (data.trend_direction) {
      case "increasing":
        return {
          label: "Increasing",
          className:
            "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
        }
      case "decreasing":
        return {
          label: "Decreasing",
          className:
            "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
        }
      default:
        return {
          label: "Stable",
          className: "bg-muted text-muted-foreground",
        }
    }
  })()

  const chartData: ChartPoint[] = [
    ...data.historical
      .sort((a, b) => a.date.localeCompare(b.date))
      .map((d) => ({
        date: format(parseISO(d.date), "MMM d"),
        cost: d.estimated_cost,
      })),
    ...data.forecast
      .sort((a, b) => a.date.localeCompare(b.date))
      .map((d) => ({
        date: format(parseISO(d.date), "MMM d"),
        projected_cost: d.projected_cost,
        upper_bound: d.upper_bound,
        lower_bound: d.lower_bound,
      })),
  ]

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-xs font-medium text-muted-foreground">Monthly Projection</p>
          <p className="mt-1 text-2xl font-semibold">{formatCost(data.monthly_projection)}</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-xs font-medium text-muted-foreground">Trend</p>
          <div className="mt-1">
            <span
              className={cn(
                "inline-flex items-center rounded-full px-2.5 py-1 text-sm font-medium",
                trendBadge.className,
              )}
            >
              {trendBadge.label}
            </span>
          </div>
        </div>
      </div>

      {chartData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Cost Forecast</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={320}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="colorHistorical" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={CHART_COLORS.tertiary} stopOpacity={0.2} />
                    <stop offset="95%" stopColor={CHART_COLORS.tertiary} stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorForecastBand" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={CHART_COLORS.secondary} stopOpacity={0.15} />
                    <stop offset="95%" stopColor={CHART_COLORS.secondary} stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis dataKey="date" tick={AXIS_TICK_STYLE} />
                <YAxis
                  tickFormatter={(v) => formatCost(v as number)}
                  tick={AXIS_TICK_STYLE}
                />
                <Tooltip content={<ChartTooltip formatter={(v) => formatCost(v)} />} />
                <Area
                  type="monotone"
                  dataKey="cost"
                  stroke={CHART_COLORS.tertiary}
                  fill="url(#colorHistorical)"
                  strokeWidth={2}
                  name="Actual Cost"
                  connectNulls={false}
                />
                <Area
                  type="monotone"
                  dataKey="upper_bound"
                  stroke="none"
                  fill="url(#colorForecastBand)"
                  name="Upper Bound"
                  connectNulls={false}
                />
                <Area
                  type="monotone"
                  dataKey="lower_bound"
                  stroke="none"
                  fill="transparent"
                  name="Lower Bound"
                  connectNulls={false}
                />
                <Area
                  type="monotone"
                  dataKey="projected_cost"
                  stroke={CHART_COLORS.secondary}
                  fill="none"
                  strokeWidth={2}
                  strokeDasharray="6 4"
                  name="Projected"
                  connectNulls={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
