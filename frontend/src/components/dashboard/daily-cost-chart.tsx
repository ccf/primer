import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { DailyCostEntry } from "@/types/api"
import { format, parseISO } from "date-fns"
import { formatCost } from "@/lib/utils"

interface DailyCostChartProps {
  data: DailyCostEntry[]
}

export function DailyCostChart({ data }: DailyCostChartProps) {
  const chartData = [...data]
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((d) => ({
      date: format(parseISO(d.date), "MMM d"),
      cost: d.estimated_cost,
    }))

  if (chartData.length === 0) return null

  return (
    <Card className="col-span-full">
      <CardHeader>
        <CardTitle className="text-sm font-medium">Daily Estimated Cost</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="colorCost" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} />
            <YAxis tickFormatter={(v) => formatCost(v as number)} tick={{ fontSize: 11 }} />
            <Tooltip formatter={(v) => formatCost(v as number)} />
            <Area
              type="monotone"
              dataKey="cost"
              stroke="#f59e0b"
              fill="url(#colorCost)"
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
