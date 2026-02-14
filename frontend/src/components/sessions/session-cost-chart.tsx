import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { ModelUsageResponse } from "@/types/api"
import { estimateModelCost, formatCost } from "@/lib/utils"

interface SessionCostChartProps {
  data: ModelUsageResponse[]
}

const COLORS = ["#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6"]

export function SessionCostChart({ data }: SessionCostChartProps) {
  const chartData = data.map((m) => {
    const cost = estimateModelCost(m.model_name, m)
    return {
      name: m.model_name.replace(/^claude-/, "").split("-202")[0],
      cost,
      fullName: m.model_name,
    }
  })

  const totalCost = chartData.reduce((sum, d) => sum + d.cost, 0)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">
          Cost Breakdown
          <span className="ml-2 text-xs font-normal text-muted-foreground">
            {formatCost(totalCost)}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-4">
          <ResponsiveContainer width={120} height={120}>
            <PieChart>
              <Pie
                data={chartData}
                dataKey="cost"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={30}
                outerRadius={50}
                strokeWidth={1}
              >
                {chartData.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(v) => formatCost(Number(v))} />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-1.5">
            {chartData.map((d, i) => (
              <div key={d.fullName} className="flex items-center gap-2 text-xs">
                <div className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                <span className="text-muted-foreground">{d.name}</span>
                <span className="font-medium">{formatCost(d.cost)}</span>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
