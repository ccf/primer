import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
  Cell,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartTooltip } from "@/components/charts/chart-tooltip"
import { CHART_COLORS, AXIS_TICK_STYLE } from "@/lib/chart-colors"
import { useCostModeling } from "@/hooks/use-api-queries"
import { CardSkeleton, ChartSkeleton, TableSkeleton } from "@/components/shared/loading-skeleton"
import { formatCost, cn } from "@/lib/utils"

const TIER_COLORS: Record<string, string> = {
  api_key: CHART_COLORS.primary,
  pro: CHART_COLORS.secondary,
  max_5x: CHART_COLORS.tertiary,
  max_20x: CHART_COLORS.quaternary,
}

const TIER_BADGE_STYLES: Record<string, string> = {
  api_key: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400",
  pro: "bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400",
  max_5x: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  max_20x: "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400",
}

interface ModelingTabProps {
  teamId: string | null
  startDate?: string
  endDate?: string
}

export function ModelingTab({ teamId, startDate, endDate }: ModelingTabProps) {
  const { data, isLoading } = useCostModeling(teamId, startDate, endDate)

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-3">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
        <ChartSkeleton />
        <TableSkeleton />
      </div>
    )
  }

  if (!data) return null

  const savings = data.total_savings_monthly
  const savingsPositive = savings > 0

  // KPI cards
  const summaryCards = [
    {
      label: "All-API Cost/mo",
      value: formatCost(data.total_api_cost_monthly),
    },
    {
      label: "Optimal Mix Cost/mo",
      value: formatCost(data.total_optimal_cost_monthly),
    },
    {
      label: "Monthly Savings",
      value: formatCost(savings),
      positive: savingsPositive,
    },
  ]

  // Allocation pills
  const allocPills = data.allocation.filter((a) => a.engineer_count > 0)

  // Efficient frontier chart data — sorted by monthly API cost ascending
  const sortedEngineers = [...data.engineers].sort(
    (a, b) => a.monthly_api_cost - b.monthly_api_cost,
  )
  const chartData = sortedEngineers.map((e) => ({
    name: e.engineer_name,
    plan_cost: e.recommended_plan_cost,
    api_cost: e.monthly_api_cost,
    tier: e.recommended_plan,
  }))

  // Tier label lookup
  const tierLabelMap: Record<string, string> = {}
  for (const t of data.plan_tiers) {
    tierLabelMap[t.name] = t.label
  }

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        {summaryCards.map((card) => (
          <div key={card.label} className="rounded-lg border border-border bg-card p-4">
            <p className="text-xs font-medium text-muted-foreground">{card.label}</p>
            <p
              className={cn(
                "mt-1 text-2xl font-semibold",
                card.positive != null &&
                  (card.positive
                    ? "text-emerald-600 dark:text-emerald-400"
                    : "text-red-600 dark:text-red-400"),
              )}
            >
              {card.value}
            </p>
          </div>
        ))}
      </div>

      {/* Allocation Pills */}
      {allocPills.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-muted-foreground">Optimal allocation:</span>
          {allocPills.map((a) => (
            <span
              key={a.plan}
              className={cn(
                "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium",
                TIER_BADGE_STYLES[a.plan] ?? "bg-muted text-muted-foreground",
              )}
            >
              {a.engineer_count} {a.label}
            </span>
          ))}
        </div>
      )}

      {/* Efficient Frontier Chart */}
      {chartData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">
              Efficient Frontier: Optimal Plan vs API Cost
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={320}>
              <ComposedChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis
                  dataKey="name"
                  tick={AXIS_TICK_STYLE}
                  interval={0}
                  angle={chartData.length > 8 ? -35 : 0}
                  textAnchor={chartData.length > 8 ? "end" : "middle"}
                  height={chartData.length > 8 ? 60 : 30}
                />
                <YAxis
                  tickFormatter={(v) => formatCost(v as number)}
                  tick={AXIS_TICK_STYLE}
                />
                <Tooltip
                  content={<ChartTooltip formatter={(v) => formatCost(v)} />}
                />
                {/* Tier boundary reference lines */}
                <ReferenceLine
                  y={20}
                  stroke="var(--color-muted-foreground)"
                  strokeDasharray="4 4"
                  strokeOpacity={0.4}
                  label={{
                    value: "Pro $20",
                    position: "right",
                    fill: "var(--color-muted-foreground)",
                    fontSize: 10,
                  }}
                />
                <ReferenceLine
                  y={100}
                  stroke="var(--color-muted-foreground)"
                  strokeDasharray="4 4"
                  strokeOpacity={0.4}
                  label={{
                    value: "Max 5x $100",
                    position: "right",
                    fill: "var(--color-muted-foreground)",
                    fontSize: 10,
                  }}
                />
                <ReferenceLine
                  y={200}
                  stroke="var(--color-muted-foreground)"
                  strokeDasharray="4 4"
                  strokeOpacity={0.4}
                  label={{
                    value: "Max 20x $200",
                    position: "right",
                    fill: "var(--color-muted-foreground)",
                    fontSize: 10,
                  }}
                />
                {/* Recommended plan cost bars — colored by tier */}
                <Bar dataKey="plan_cost" name="Optimal Plan Cost" radius={[3, 3, 0, 0]}>
                  {chartData.map((entry, idx) => (
                    <Cell
                      key={idx}
                      fill={TIER_COLORS[entry.tier] ?? CHART_COLORS.primary}
                    />
                  ))}
                </Bar>
                {/* API cost line overlay */}
                <Line
                  type="monotone"
                  dataKey="api_cost"
                  name="Monthly API Cost"
                  stroke={CHART_COLORS.quinary}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
              </ComposedChart>
            </ResponsiveContainer>
            <p className="mt-2 text-xs text-muted-foreground">
              Where the line is above the bars, a subscription plan saves money. Where it's below, API is cheaper.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Engineer Table */}
      {data.engineers.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Engineer Cost Comparison</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-muted-foreground">
                    <th className="pb-2 pr-4 font-medium">Engineer</th>
                    <th className="pb-2 pr-4 font-medium">Current Mode</th>
                    <th className="pb-2 pr-4 font-medium text-right">API Cost/mo</th>
                    <th className="pb-2 pr-4 font-medium">Recommended</th>
                    <th className="pb-2 pr-4 font-medium text-right">Plan Cost/mo</th>
                    <th className="pb-2 font-medium text-right">Savings</th>
                  </tr>
                </thead>
                <tbody>
                  {data.engineers
                    .slice()
                    .sort((a, b) => b.savings_vs_api - a.savings_vs_api)
                    .map((eng) => (
                      <tr
                        key={eng.engineer_id}
                        className="border-b border-border/40 last:border-0"
                      >
                        <td className="py-2.5 pr-4 font-medium">{eng.engineer_name}</td>
                        <td className="py-2.5 pr-4">
                          <span className="text-xs text-muted-foreground">
                            {eng.current_billing_mode ?? "unknown"}
                          </span>
                        </td>
                        <td className="py-2.5 pr-4 text-right">
                          {formatCost(eng.monthly_api_cost)}
                        </td>
                        <td className="py-2.5 pr-4">
                          <span
                            className={cn(
                              "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
                              TIER_BADGE_STYLES[eng.recommended_plan] ??
                                "bg-muted text-muted-foreground",
                            )}
                          >
                            {tierLabelMap[eng.recommended_plan] ?? eng.recommended_plan}
                          </span>
                        </td>
                        <td className="py-2.5 pr-4 text-right">
                          {formatCost(eng.recommended_plan_cost)}
                        </td>
                        <td
                          className={cn(
                            "py-2.5 text-right font-medium",
                            eng.savings_vs_api > 0
                              ? "text-emerald-600 dark:text-emerald-400"
                              : "",
                          )}
                        >
                          {eng.savings_vs_api > 0 ? "+" : ""}
                          {formatCost(eng.savings_vs_api)}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
