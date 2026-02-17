import { useState, useMemo } from "react"
import {
  useEngineerAnalytics,
  useEngineerBenchmarks,
  useQualityMetrics,
  useMaturityAnalytics,
} from "@/hooks/use-api-queries"
import { EngineerLeaderboard } from "@/components/engineers/engineer-leaderboard"
import { mergeEngineerData } from "@/components/engineers/merge-engineer-data"
import { TableSkeleton } from "@/components/shared/loading-skeleton"
import { EmptyState } from "@/components/shared/empty-state"

interface EngineersTabProps {
  teamId: string | null
  startDate?: string
  endDate?: string
}

export function EngineersTab({ teamId, startDate, endDate }: EngineersTabProps) {
  const [sortBy, setSortBy] = useState("total_sessions")
  const { data, isLoading } = useEngineerAnalytics(teamId, startDate, endDate, sortBy)
  const { data: benchmarks } = useEngineerBenchmarks(teamId, startDate, endDate)
  const { data: quality } = useQualityMetrics(teamId, startDate, endDate)
  const { data: maturity } = useMaturityAnalytics(teamId, startDate, endDate)

  const engineers = useMemo(
    () =>
      data?.engineers
        ? mergeEngineerData(
            data.engineers,
            benchmarks?.engineers,
            quality?.engineer_quality,
            maturity?.engineer_profiles,
          )
        : [],
    [data, benchmarks, quality, maturity],
  )

  if (isLoading) return <TableSkeleton />

  if (!data || data.engineers.length === 0) {
    return <EmptyState message="No engineers found" />
  }

  return (
    <EngineerLeaderboard
      engineers={engineers}
      benchmark={benchmarks?.benchmark}
      onSortChange={setSortBy}
      sortBy={sortBy}
    />
  )
}
