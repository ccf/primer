import { useState } from "react"
import { useAuth } from "@/lib/auth-context"
import { getApiKey } from "@/lib/api"
import { useEngineerAnalytics, useEngineerBenchmarks } from "@/hooks/use-api-queries"
import { EngineerLeaderboard } from "@/components/engineers/engineer-leaderboard"
import { BenchmarkTable } from "@/components/engineers/benchmark-table"
import { TableSkeleton } from "@/components/shared/loading-skeleton"
import { EmptyState } from "@/components/shared/empty-state"
import type { DateRange } from "@/components/layout/date-range-picker"

interface EngineersPageProps {
  teamId: string | null
  dateRange: DateRange | null
}

export function EngineersPage({ teamId, dateRange }: EngineersPageProps) {
  const { user } = useAuth()
  const isApiKeyUser = !user && !!getApiKey()
  const role = user?.role ?? (isApiKeyUser ? "admin" : "engineer")
  const canBenchmark = role === "team_lead" || role === "admin"

  const [sortBy, setSortBy] = useState("total_sessions")
  const startDate = dateRange?.startDate
  const endDate = dateRange?.endDate
  const { data, isLoading } = useEngineerAnalytics(teamId, startDate, endDate, sortBy)
  const { data: benchmarks, isLoading: loadingBenchmarks } = useEngineerBenchmarks(
    teamId,
    startDate,
    endDate,
    canBenchmark,
  )

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Engineers</h1>
        <TableSkeleton />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Engineers</h1>

      {/* Benchmark Table for team_lead / admin */}
      {canBenchmark && (
        loadingBenchmarks ? (
          <TableSkeleton />
        ) : benchmarks && benchmarks.engineers.length > 0 ? (
          <BenchmarkTable
            engineers={benchmarks.engineers}
            benchmark={benchmarks.benchmark}
          />
        ) : null
      )}

      {!data || data.engineers.length === 0 ? (
        <EmptyState message="No engineers found" />
      ) : (
        <EngineerLeaderboard
          engineers={data.engineers}
          onSortChange={setSortBy}
          sortBy={sortBy}
        />
      )}
    </div>
  )
}
