import type {
  EngineerStats,
  EngineerBenchmark,
  EngineerQuality,
  EngineerLeverageProfile,
} from "@/types/api"
import type { UnifiedEngineerRow } from "./engineer-leaderboard"

/** Merge data from multiple API sources into unified rows. */
export function mergeEngineerData(
  stats: EngineerStats[],
  benchmarks?: EngineerBenchmark[],
  quality?: EngineerQuality[],
  leverage?: EngineerLeverageProfile[],
): UnifiedEngineerRow[] {
  const benchmarkMap = new Map(benchmarks?.map((b) => [b.engineer_id, b]))
  const qualityMap = new Map(quality?.map((q) => [q.engineer_id, q]))
  const leverageMap = new Map(leverage?.map((l) => [l.engineer_id, l]))

  return stats.map((s) => {
    const b = benchmarkMap.get(s.engineer_id)
    const q = qualityMap.get(s.engineer_id)
    const l = leverageMap.get(s.engineer_id)
    return {
      engineer_id: s.engineer_id,
      name: s.name,
      display_name: b?.display_name ?? null,
      email: s.email,
      avatar_url: s.avatar_url,
      total_sessions: s.total_sessions,
      estimated_cost: s.estimated_cost,
      success_rate: s.success_rate,
      percentile_sessions: b?.percentile_sessions,
      vs_team_avg: b?.vs_team_avg,
      pr_count: q?.pr_count,
      merge_rate: q?.merge_rate,
      leverage_score: l?.leverage_score,
      _benchmark: b,
    }
  })
}
