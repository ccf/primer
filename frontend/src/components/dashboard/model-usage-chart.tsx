import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { ModelRanking } from "@/types/api"
import { formatTokens } from "@/lib/utils"

interface ModelUsageChartProps {
  data: ModelRanking[]
}

export function ModelUsageChart({ data }: ModelUsageChartProps) {
  const chartData = data.map((m) => ({
    name: m.model_name.replace(/^claude-/, "").split("-202")[0],
    input: m.total_input_tokens,
    output: m.total_output_tokens,
  }))

  if (chartData.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Model Usage (tokens)</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={chartData}>
            <XAxis dataKey="name" tick={{ fontSize: 11 }} />
            <YAxis tickFormatter={(v) => formatTokens(v as number)} tick={{ fontSize: 11 }} />
            <Tooltip formatter={(v) => formatTokens(v as number)} />
            <Legend />
            <Bar dataKey="input" fill="#6366f1" stackId="a" radius={[0, 0, 0, 0]} />
            <Bar dataKey="output" fill="#a78bfa" stackId="a" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
