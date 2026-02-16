import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import type { FrictionReport, ConfigSuggestion } from "@/types/api"

interface FrictionTabProps {
  friction: FrictionReport[]
  configSuggestions: ConfigSuggestion[]
}

const severityVariant: Record<string, "destructive" | "warning" | "secondary"> = {
  high: "destructive",
  medium: "warning",
  low: "secondary",
}

export function FrictionTab({ friction, configSuggestions }: FrictionTabProps) {
  if (friction.length === 0 && configSuggestions.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">
        No friction data or config suggestions available.
      </div>
    )
  }

  const chartData = friction
    .sort((a, b) => b.count - a.count)
    .map((f) => ({
      name: f.friction_type.replace(/_/g, " "),
      count: f.count,
    }))

  return (
    <div className="space-y-6">
      {chartData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Friction by Type</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={Math.max(200, chartData.length * 40)}>
              <BarChart data={chartData} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fontSize: 11 }}
                  width={140}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "8px",
                    fontSize: "12px",
                  }}
                />
                <Bar
                  dataKey="count"
                  fill="hsl(var(--primary))"
                  radius={[0, 4, 4, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {configSuggestions.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-medium">Config Suggestions</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            {configSuggestions.map((suggestion, i) => (
              <Card key={i}>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-2">
                    <div className="space-y-1">
                      <p className="text-sm font-medium">{suggestion.title}</p>
                      <p className="text-xs text-muted-foreground">{suggestion.description}</p>
                      {suggestion.suggested_config && (
                        <code className="mt-1 block rounded bg-muted px-2 py-1 text-xs">
                          {suggestion.suggested_config}
                        </code>
                      )}
                    </div>
                    <Badge variant={severityVariant[suggestion.severity] ?? "secondary"}>
                      {suggestion.severity}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
