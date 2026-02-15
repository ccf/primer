import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { ToolTrendEntry } from "@/types/api"
import { format, parseISO } from "date-fns"

interface ToolTrendChartProps {
  data: ToolTrendEntry[]
}

const COLORS = ["#6366f1", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6"]

export function ToolTrendChart({ data }: ToolTrendChartProps) {
  if (data.length === 0) return null

  // Group by date, pivot tool names into columns
  const toolNames = [...new Set(data.map((d) => d.tool_name))]
  const dateMap = new Map<string, Record<string, number>>()

  for (const entry of data) {
    const dateKey = entry.date
    if (!dateMap.has(dateKey)) {
      dateMap.set(dateKey, {})
    }
    dateMap.get(dateKey)![entry.tool_name] = entry.call_count
  }

  const chartData = [...dateMap.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, tools]) => ({
      date: format(parseISO(date), "MMM d"),
      ...tools,
    }))

  if (chartData.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Tool Usage Trends</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Legend />
            {toolNames.map((name, i) => (
              <Line
                key={name}
                type="monotone"
                dataKey={name}
                stroke={COLORS[i % COLORS.length]}
                strokeWidth={2}
                dot={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
