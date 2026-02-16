import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { SessionHealthDistribution } from "@/types/api"

const BUCKET_COLORS: Record<string, string> = {
  excellent: "#10b981",
  good: "#6366f1",
  fair: "#f59e0b",
  poor: "#ef4444",
}

interface Props {
  data: SessionHealthDistribution
}

export function HealthDistributionChart({ data }: Props) {
  const chartData = Object.entries(data.buckets).map(([label, count]) => ({
    label: label.charAt(0).toUpperCase() + label.slice(1),
    count,
    fill: BUCKET_COLORS[label] ?? "hsl(var(--muted-foreground))",
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle>Health Distribution</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis dataKey="label" className="text-xs fill-muted-foreground" />
            <YAxis className="text-xs fill-muted-foreground" />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "8px",
                color: "hsl(var(--foreground))",
              }}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {chartData.map((entry, i) => (
                <Cell key={i} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
