import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartTooltip } from "@/components/charts/chart-tooltip"
import { CHART_COLORS, CHART_PALETTE, AXIS_TICK_STYLE } from "@/lib/chart-colors"
import { useCacheAnalytics } from "@/hooks/use-api-queries"
import { CardSkeleton, ChartSkeleton, TableSkeleton } from "@/components/shared/loading-skeleton"
import { formatCost, formatPercent } from "@/lib/utils"
import { format, parseISO } from "date-fns"

interface CacheTabProps {
  teamId: string | null
  startDate?: string
  endDate?: string
}

export function CacheTab({ teamId, startDate, endDate }: CacheTabProps) {
  const { data, isLoading } = useCacheAnalytics(teamId, startDate, endDate)

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-3">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
        <ChartSkeleton />
        <ChartSkeleton />
        <TableSkeleton />
      </div>
    )
  }

  if (!data) return null

  const totalSavings = data.cache_savings_estimate ?? 0

  // Effective discount: savings / (savings + what was actually paid for cache reads)
  // Cache reads were charged at cache_read price; without caching they'd cost input price.
  // So actual_paid_for_cached = total via API minus savings is just the cache_read cost portion.
  // Simpler: effective discount = savings / (savings + remaining_cost_estimate)
  // We approximate: cache reads cost = total_input_cost_equivalent - savings
  // But the cleanest: discount = savings / total_input_cost_if_no_cache
  // total_input_cost_if_no_cache ≈ savings + actual_cache_read_cost
  // Since we don't have actual_cache_read_cost in the response, use model breakdown
  const modelSavingsData = data.model_cache_breakdown
    .filter((m) => m.estimated_savings > 0)
    .map((m) => ({
      model: m.model_name.replace(/^claude-/, "").split("-202")[0],
      savings: m.estimated_savings,
    }))

  // Effective discount: what % cheaper is the total bill thanks to caching
  // Best approximation without full cost data: savings / (savings / discount_depth)
  // where discount_depth is the average savings-per-cached-token / input-price-per-token
  // Simpler: show cache_savings / (some total), but we lack total spend in this response.
  // Use a practical formula: savings relative to what would have been spent on those tokens
  // This is equivalent to: avg(1 - cache_read_price/input_price) across models
  // Which is always ~90% for Opus, ~90% for Sonnet. So just show hit_rate * avg_discount_depth.
  // Actually let's compute it from model data properly:
  let totalWouldHaveCost = 0
  for (const m of data.model_cache_breakdown) {
    if (m.cache_read_tokens > 0 && m.estimated_savings > 0) {
      // savings = cr * (input_price - cache_price)
      // would_have = cr * input_price = savings + cr * cache_price
      // savings / would_have = (input_price - cache_price) / input_price
      // would_have = savings / (1 - cache_price/input_price)
      // For Claude models cache is 10% of input, so would_have ≈ savings / 0.9
      // But let's be precise: would_have = savings * cr / cr (cancel out) -- we need ratio
      // Actually: would_have = savings + actual_cache_cost
      // actual_cache_cost = would_have - savings
      // We know: savings/would_have = 1 - cache_price/input_price
      // For all Claude models: cache_read = input/10, so ratio = 0.9
      // would_have = savings / 0.9 -- this is a very close approximation
      totalWouldHaveCost += m.estimated_savings / 0.9
    }
  }
  const effectiveDiscount = totalWouldHaveCost > 0 ? totalSavings / totalWouldHaveCost : null

  const potentialSavings = data.total_potential_additional_savings ?? 0

  // --- Savings by model chart data ---
  const savingsByModel = modelSavingsData.sort((a, b) => b.savings - a.savings)

  // --- Daily savings trend ---
  // Derive avg savings per cached token from totals
  const totalCacheRead = data.total_cache_read_tokens
  const avgSavingsPerToken = totalCacheRead > 0 ? totalSavings / totalCacheRead : 0

  const dailySavingsData = [...data.daily_cache_trend]
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((d) => ({
      date: format(parseISO(d.date), "MMM d"),
      savings: Math.round(d.cache_read_tokens * avgSavingsPerToken * 100) / 100,
    }))

  // --- Engineer table ---
  const engineers = data.engineer_cache_breakdown ?? []
  const teamAvgHitRate = data.cache_hit_rate

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-xs font-medium text-muted-foreground">Cache Savings</p>
          <p className="mt-1 text-2xl font-semibold text-emerald-600 dark:text-emerald-400">
            {formatCost(totalSavings)}
          </p>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-xs font-medium text-muted-foreground">Effective Discount</p>
          <p className="mt-1 text-2xl font-semibold">
            {effectiveDiscount != null ? formatPercent(effectiveDiscount) : "-"}
          </p>
          <p className="mt-0.5 text-[11px] text-muted-foreground">
            reduction on cached token cost
          </p>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-xs font-medium text-muted-foreground">Potential Additional Savings</p>
          <p className="mt-1 text-2xl font-semibold text-amber-600 dark:text-amber-400">
            {potentialSavings > 0 ? formatCost(potentialSavings) : "-"}
          </p>
          <p className="mt-0.5 text-[11px] text-muted-foreground">
            if all engineers match team avg
          </p>
        </div>
      </div>

      {/* Savings by Model — Horizontal Bar Chart */}
      {savingsByModel.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Savings by Model</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={Math.max(savingsByModel.length * 44, 120)}>
              <BarChart data={savingsByModel} layout="vertical" margin={{ left: 10, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" horizontal={false} />
                <XAxis
                  type="number"
                  tickFormatter={(v) => formatCost(v as number)}
                  tick={AXIS_TICK_STYLE}
                />
                <YAxis
                  type="category"
                  dataKey="model"
                  tick={AXIS_TICK_STYLE}
                  width={120}
                />
                <Tooltip
                  content={<ChartTooltip formatter={(v) => formatCost(v as number)} />}
                />
                <Bar dataKey="savings" name="Savings" radius={[0, 4, 4, 0]}>
                  {savingsByModel.map((_, i) => (
                    <Cell key={i} fill={CHART_PALETTE[i % CHART_PALETTE.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Daily Savings Trend */}
      {dailySavingsData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Daily Cache Savings</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={dailySavingsData}>
                <defs>
                  <linearGradient id="colorDailySavings" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={CHART_COLORS.primary} stopOpacity={0.2} />
                    <stop offset="95%" stopColor={CHART_COLORS.primary} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis dataKey="date" tick={AXIS_TICK_STYLE} />
                <YAxis
                  tickFormatter={(v) => formatCost(v as number)}
                  tick={AXIS_TICK_STYLE}
                />
                <Tooltip
                  content={<ChartTooltip formatter={(v) => formatCost(v as number)} />}
                />
                <Area
                  type="monotone"
                  dataKey="savings"
                  stroke={CHART_COLORS.primary}
                  fill="url(#colorDailySavings)"
                  strokeWidth={2}
                  name="Savings"
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Per-Engineer Cache Efficiency Table */}
      {engineers.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">
              Per-Engineer Cache Efficiency
              {teamAvgHitRate != null && (
                <span className="ml-2 text-xs font-normal text-muted-foreground">
                  Team avg: {formatPercent(teamAvgHitRate)}
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-muted-foreground">
                    <th className="pb-2 pr-4 font-medium">Engineer</th>
                    <th className="pb-2 pr-4 font-medium text-right">Hit Rate</th>
                    <th className="pb-2 pr-4 font-medium text-right">Savings</th>
                    <th className="pb-2 font-medium text-right">Potential Upside</th>
                  </tr>
                </thead>
                <tbody>
                  {engineers.map((eng) => (
                    <tr
                      key={eng.engineer_id}
                      className="border-b border-border/40 last:border-0"
                    >
                      <td className="py-2.5 pr-4 font-medium">{eng.engineer_name}</td>
                      <td className="py-2.5 pr-4 text-right">
                        {formatPercent(eng.cache_hit_rate)}
                      </td>
                      <td className="py-2.5 pr-4 text-right text-emerald-600 dark:text-emerald-400">
                        {formatCost(eng.estimated_savings)}
                      </td>
                      <td className="py-2.5 text-right">
                        {eng.potential_additional_savings > 0 ? (
                          <span className="text-amber-600 dark:text-amber-400">
                            {formatCost(eng.potential_additional_savings)}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
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
