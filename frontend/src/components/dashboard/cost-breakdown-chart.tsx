import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { ModelCostBreakdown } from "@/types/api"
import { formatCost } from "@/lib/utils"

interface CostBreakdownChartProps {
  data: ModelCostBreakdown[]
}

export function CostBreakdownChart({ data }: CostBreakdownChartProps) {
  const chartData = data.map((m) => ({
    name: m.model_name.replace(/^claude-/, "").split("-202")[0],
    cost: m.estimated_cost,
  }))

  if (chartData.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Cost by Model</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={chartData}>
            <XAxis dataKey="name" tick={{ fontSize: 11 }} />
            <YAxis tickFormatter={(v) => formatCost(v as number)} tick={{ fontSize: 11 }} />
            <Tooltip formatter={(v) => formatCost(v as number)} />
            <Legend />
            <Bar dataKey="cost" fill="#f59e0b" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
