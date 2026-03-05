import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Label,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { CHART_COLORS } from "@/lib/chart-colors"
import type { EngineerLeverageProfile } from "@/types/api"

interface EffectivenessScatterProps {
  data: EngineerLeverageProfile[]
}

interface ScatterPoint {
  name: string
  leverage: number
  effectiveness: number
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: { payload: ScatterPoint }[] }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="rounded-lg border border-border bg-card px-3 py-2 text-xs shadow-lg">
      <p className="font-medium">{d.name}</p>
      <p className="text-muted-foreground">
        Leverage: <span className="font-medium text-foreground">{d.leverage.toFixed(1)}</span>
      </p>
      <p className="text-muted-foreground">
        Effectiveness: <span className="font-medium text-foreground">{d.effectiveness.toFixed(1)}</span>
      </p>
    </div>
  )
}

export function EffectivenessScatter({ data }: EffectivenessScatterProps) {
  const points: ScatterPoint[] = data
    .filter((p) => p.effectiveness_score != null)
    .map((p) => ({
      name: p.name,
      leverage: p.leverage_score,
      effectiveness: p.effectiveness_score!,
    }))

  if (points.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Leverage vs Effectiveness</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="py-12 text-center text-sm text-muted-foreground">
            No effectiveness data available yet. Effectiveness scores require session outcome data.
          </p>
        </CardContent>
      </Card>
    )
  }

  // Compute medians for quadrant lines
  const median = (vals: number[]) => {
    const s = [...vals].sort((a, b) => a - b)
    const mid = Math.floor(s.length / 2)
    return s.length % 2 === 0 ? (s[mid - 1] + s[mid]) / 2 : s[mid]
  }
  const medianLeverage = median(points.map((p) => p.leverage))
  const medianEffectiveness = median(points.map((p) => p.effectiveness))

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">Leverage vs Effectiveness</CardTitle>
        <p className="text-xs text-muted-foreground">
          Each dot is an engineer. Quadrants show coaching opportunities.
        </p>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={400}>
          <ScatterChart margin={{ top: 20, right: 30, bottom: 20, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
            <XAxis
              type="number"
              dataKey="leverage"
              domain={[0, 100]}
              tick={{ fontSize: 11 }}
              tickLine={false}
            >
              <Label value="Leverage (sophistication)" position="bottom" offset={0} className="text-xs fill-muted-foreground" />
            </XAxis>
            <YAxis
              type="number"
              dataKey="effectiveness"
              domain={[0, 100]}
              tick={{ fontSize: 11 }}
              tickLine={false}
            >
              <Label
                value="Effectiveness (outcomes)"
                angle={-90}
                position="insideLeft"
                offset={10}
                className="text-xs fill-muted-foreground"
              />
            </YAxis>
            <ReferenceLine
              x={medianLeverage}
              stroke="var(--color-border)"
              strokeDasharray="4 4"
              strokeWidth={1}
            />
            <ReferenceLine
              y={medianEffectiveness}
              stroke="var(--color-border)"
              strokeDasharray="4 4"
              strokeWidth={1}
            />
            <Tooltip content={<CustomTooltip />} />
            <Scatter
              data={points}
              fill={CHART_COLORS.primary}
              fillOpacity={0.7}
              r={6}
            />
          </ScatterChart>
        </ResponsiveContainer>
        <div className="mt-2 grid grid-cols-2 gap-2 text-[10px] text-muted-foreground">
          <div className="rounded-md bg-muted/50 px-2 py-1">
            <span className="font-medium text-foreground">Top-left:</span> Efficient basics — ships results, could level up
          </div>
          <div className="rounded-md bg-muted/50 px-2 py-1">
            <span className="font-medium text-foreground">Top-right:</span> Mastery — advanced tools, strong outcomes
          </div>
          <div className="rounded-md bg-muted/50 px-2 py-1">
            <span className="font-medium text-foreground">Bottom-left:</span> Needs support — both tool usage and outcomes lag
          </div>
          <div className="rounded-md bg-muted/50 px-2 py-1">
            <span className="font-medium text-foreground">Bottom-right:</span> Experimenting — sophisticated but outcomes lag
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
