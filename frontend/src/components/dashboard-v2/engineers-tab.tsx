import { useState } from "react"
import { useEngineerAnalytics, useEngineerBenchmarks } from "@/hooks/use-api-queries"
import { EngineerLeaderboard } from "@/components/engineers/engineer-leaderboard"
import { BenchmarkTable } from "@/components/engineers/benchmark-table"
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
  const { data: benchmarks, isLoading: loadingBenchmarks } = useEngineerBenchmarks(teamId, startDate, endDate)

  if (isLoading) return <TableSkeleton />

  return (
    <div className="space-y-6">
      {loadingBenchmarks ? (
        <TableSkeleton />
      ) : benchmarks && benchmarks.engineers.length > 0 ? (
        <BenchmarkTable engineers={benchmarks.engineers} benchmark={benchmarks.benchmark} />
      ) : null}

      {!data || data.engineers.length === 0 ? (
        <EmptyState message="No engineers found" />
      ) : (
        <EngineerLeaderboard engineers={data.engineers} onSortChange={setSortBy} sortBy={sortBy} />
      )}
    </div>
  )
}
