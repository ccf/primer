import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { PrimarySuccessAnalysis } from "@/types/api"

const COLORS = {
  full: "#10b981",
  partial: "#f59e0b",
  none: "#ef4444",
  unknown: "#94a3b8",
}

interface Props {
  data: PrimarySuccessAnalysis
}

export function PrimarySuccessChart({ data }: Props) {
  const chartData = [
    { name: "Full", value: data.full_count, fill: COLORS.full },
    { name: "Partial", value: data.partial_count, fill: COLORS.partial },
    { name: "None", value: data.none_count, fill: COLORS.none },
    { name: "Unknown", value: data.unknown_count, fill: COLORS.unknown },
  ].filter((d) => d.value > 0)

  if (chartData.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle>Primary Success</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={250}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={90}
              dataKey="value"
              nameKey="name"
            >
              {chartData.map((entry, i) => (
                <Cell key={i} fill={entry.fill} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "8px",
                color: "hsl(var(--foreground))",
              }}
            />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
