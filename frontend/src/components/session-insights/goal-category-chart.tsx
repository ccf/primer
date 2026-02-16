import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { GoalCategoryBreakdown } from "@/types/api"

interface Props {
  data: GoalCategoryBreakdown[]
}

export function GoalCategoryChart({ data }: Props) {
  if (data.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle>Goal Categories</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={Math.max(200, data.length * 40)}>
          <BarChart data={data} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis type="number" className="text-xs fill-muted-foreground" />
            <YAxis dataKey="category" type="category" className="text-xs fill-muted-foreground" width={120} />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "8px",
                color: "hsl(var(--foreground))",
              }}
            />
            <Bar dataKey="count" fill="#6366f1" radius={[0, 4, 4, 0]} name="Sessions" />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
