import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { ToolAdoptionEntry } from "@/types/api"

interface ToolAdoptionChartProps {
  data: ToolAdoptionEntry[]
}

export function ToolAdoptionChart({ data }: ToolAdoptionChartProps) {
  const chartData = data.slice(0, 15).map((t) => ({
    name: t.tool_name,
    adoptionRate: t.adoption_rate,
    totalCalls: t.total_calls,
    engineers: t.engineer_count,
  }))

  if (chartData.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Tool Adoption Rate</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={Math.max(300, chartData.length * 32)}>
          <BarChart data={chartData} layout="vertical">
            <XAxis
              type="number"
              tick={{ fontSize: 11 }}
              domain={[0, 100]}
              tickFormatter={(v) => `${v}%`}
            />
            <YAxis dataKey="name" type="category" width={100} tick={{ fontSize: 11 }} />
            <Tooltip
              formatter={(value, name) => {
                if (name === "Adoption Rate") return `${value}%`
                return value
              }}
            />
            <Bar dataKey="adoptionRate" name="Adoption Rate" radius={[0, 4, 4, 0]}>
              {chartData.map((_, index) => (
                <Cell key={index} fill={index < 3 ? "#6366f1" : "#a5b4fc"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
