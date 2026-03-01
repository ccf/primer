import { useState } from "react"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts"
import { ChevronDown, ChevronRight } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ChartTooltip } from "@/components/charts/chart-tooltip"
import { CHART_COLORS, AXIS_TICK_STYLE } from "@/lib/chart-colors"
import type { FrictionReport, ConfigSuggestion } from "@/types/api"

interface FrictionTabProps {
  friction: FrictionReport[]
  configSuggestions: ConfigSuggestion[]
}

const severityVariant: Record<string, "destructive" | "warning" | "secondary" | "info"> = {
  high: "destructive",
  medium: "warning",
  low: "secondary",
  info: "info",
  warning: "warning",
}

export function FrictionTab({ friction, configSuggestions }: FrictionTabProps) {
  const [expanded, setExpanded] = useState<string | null>(null)

  if (friction.length === 0 && configSuggestions.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">
        No friction detected — nice work!
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
                <XAxis type="number" tick={AXIS_TICK_STYLE} allowDecimals={false} />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={AXIS_TICK_STYLE}
                  width={140}
                />
                <Tooltip content={<ChartTooltip />} />
                <Bar
                  dataKey="count"
                  fill={CHART_COLORS.primary}
                  radius={[0, 4, 4, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {friction.length > 0 && friction.some((f) => f.details.length > 0) && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Friction Details</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {friction.map((f) => (
                <div key={f.friction_type} className="rounded-xl border border-border/60">
                  <div className="flex w-full items-center justify-between p-3 text-sm">
                    <button
                      onClick={() =>
                        setExpanded(expanded === f.friction_type ? null : f.friction_type)
                      }
                      className="flex items-center gap-3 text-left hover:text-foreground"
                    >
                      {expanded === f.friction_type ? (
                        <ChevronDown className="h-4 w-4 text-muted-foreground" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-muted-foreground" />
                      )}
                      <span className="font-medium">
                        {f.friction_type.replace(/_/g, " ")}
                      </span>
                    </button>
                    <Badge variant="secondary">{f.count}</Badge>
                  </div>
                  {expanded === f.friction_type && f.details.length > 0 && (
                    <div className="border-t border-border px-4 py-3">
                      <ul className="space-y-1">
                        {f.details.map((d, i) => (
                          <li key={i} className="text-sm text-muted-foreground">
                            {d}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {configSuggestions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Config Suggestions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 sm:grid-cols-2">
              {configSuggestions.map((suggestion, i) => (
                <Card
                  key={i}
                  className="animate-stagger-in"
                  style={{ animationDelay: `${i * 60}ms` }}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between gap-2">
                      <div className="space-y-1">
                        <p className="text-sm font-medium">{suggestion.title}</p>
                        <p className="text-xs text-muted-foreground">{suggestion.description}</p>
                        {suggestion.suggested_config && (
                          <code className="mt-1 block rounded border border-border/60 bg-muted px-2 py-1 text-xs">
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
          </CardContent>
        </Card>
      )}
    </div>
  )
}
