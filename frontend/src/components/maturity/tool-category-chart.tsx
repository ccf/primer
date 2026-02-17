import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import type { ToolCategoryBreakdown } from "@/types/api"

const CATEGORY_COLORS: Record<string, string> = {
  core: "var(--color-chart-1, #6366f1)",
  search: "var(--color-chart-2, #8b5cf6)",
  orchestration: "var(--color-chart-3, #ec4899)",
  skill: "var(--color-chart-4, #f59e0b)",
  mcp: "var(--color-chart-5, #10b981)",
}

const CATEGORY_LABELS: Record<string, string> = {
  core: "Core",
  search: "Search",
  orchestration: "Orchestration",
  skill: "Skills",
  mcp: "MCP / Custom",
}

interface ToolCategoryChartProps {
  data: ToolCategoryBreakdown
}

export function ToolCategoryChart({ data }: ToolCategoryChartProps) {
  const chartData = (Object.entries(data) as [string, Record<string, number>][])
    .map(([category, tools]) => ({
      name: CATEGORY_LABELS[category] ?? category,
      value: Object.values(tools).reduce((a: number, b: number) => a + b, 0),
      category,
    }))
    .filter((d) => d.value > 0)

  if (chartData.length === 0) {
    return (
      <Card>
        <CardHeader>
          <h3 className="text-sm font-medium">Tool Categories</h3>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No tool usage data available.</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <h3 className="text-sm font-medium">Tool Categories</h3>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={280}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={100}
              paddingAngle={2}
              dataKey="value"
            >
              {chartData.map((entry) => (
                <Cell key={entry.category} fill={CATEGORY_COLORS[entry.category]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(v) => `${Number(v).toLocaleString()} calls`}
              contentStyle={{ fontSize: 12 }}
            />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
