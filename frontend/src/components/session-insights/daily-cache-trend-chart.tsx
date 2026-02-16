import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { DailyCacheEntry } from "@/types/api"

interface Props {
  data: DailyCacheEntry[]
}

export function DailyCacheTrendChart({ data }: Props) {
  if (data.length === 0) return null

  const formatted = data.map((d) => ({
    ...d,
    cache_hit_pct: d.cache_hit_rate != null ? +(d.cache_hit_rate * 100).toFixed(1) : null,
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle>Cache Efficiency Trend</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={formatted}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis dataKey="date" className="text-xs fill-muted-foreground" />
            <YAxis domain={[0, 100]} className="text-xs fill-muted-foreground" unit="%" />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "8px",
                color: "hsl(var(--foreground))",
              }}
              formatter={(value: number | undefined) => [`${value ?? 0}%`, "Cache Hit Rate"]}
            />
            <Line
              type="monotone"
              dataKey="cache_hit_pct"
              stroke="#10b981"
              strokeWidth={2}
              dot={{ r: 3 }}
              name="Cache Hit Rate"
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
