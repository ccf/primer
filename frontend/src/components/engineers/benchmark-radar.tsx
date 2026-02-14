import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
} from "recharts"
import type { EngineerBenchmark, BenchmarkContext } from "@/types/api"

interface BenchmarkRadarProps {
  engineer: EngineerBenchmark
  benchmark: BenchmarkContext
}

export function BenchmarkRadar({ engineer, benchmark }: BenchmarkRadarProps) {
  // Normalize each dimension to 0-100 relative to team avg (50 = team avg)
  function normalize(value: number | null, avg: number | null): number {
    if (value == null || avg == null || avg === 0) return 50
    const ratio = value / avg
    return Math.min(Math.max(ratio * 50, 0), 100)
  }

  const data = [
    {
      metric: "Sessions",
      engineer: normalize(engineer.total_sessions, benchmark.team_avg_sessions),
      team: 50,
    },
    {
      metric: "Tokens",
      engineer: normalize(engineer.total_tokens, benchmark.team_avg_tokens),
      team: 50,
    },
    {
      metric: "Cost Eff.",
      // Invert cost: lower cost = better efficiency
      engineer: benchmark.team_avg_cost > 0
        ? normalize(benchmark.team_avg_cost, engineer.estimated_cost)
        : 50,
      team: 50,
    },
    {
      metric: "Success",
      engineer: normalize(
        engineer.success_rate != null ? engineer.success_rate * 100 : null,
        benchmark.team_avg_success_rate * 100,
      ),
      team: 50,
    },
    {
      metric: "Duration",
      engineer: normalize(engineer.avg_duration, benchmark.team_avg_duration),
      team: 50,
    },
  ]

  return (
    <ResponsiveContainer width="100%" height={250}>
      <RadarChart data={data} cx="50%" cy="50%" outerRadius="75%">
        <PolarGrid strokeDasharray="3 3" />
        <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11 }} />
        <Radar
          name="Team Avg"
          dataKey="team"
          stroke="var(--color-muted-foreground)"
          fill="transparent"
          strokeWidth={1.5}
          strokeDasharray="4 4"
        />
        <Radar
          name={engineer.display_name ?? engineer.name}
          dataKey="engineer"
          stroke="var(--color-primary)"
          fill="var(--color-primary)"
          fillOpacity={0.15}
          strokeWidth={2}
        />
      </RadarChart>
    </ResponsiveContainer>
  )
}
