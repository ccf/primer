import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { DailyHealthEntry } from "@/types/api"

interface Props {
  data: DailyHealthEntry[]
}

export function DailyHealthTrendChart({ data }: Props) {
  if (data.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle>Health Score Trend</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis dataKey="date" className="text-xs fill-muted-foreground" />
            <YAxis domain={[0, 100]} className="text-xs fill-muted-foreground" />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "8px",
                color: "hsl(var(--foreground))",
              }}
            />
            <Line
              type="monotone"
              dataKey="avg_score"
              stroke="#6366f1"
              strokeWidth={2}
              dot={{ r: 3 }}
              name="Avg Score"
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
