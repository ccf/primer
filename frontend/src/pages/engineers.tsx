import { useState } from "react"
import { useAuth } from "@/lib/auth-context"
import { getApiKey } from "@/lib/api"
import { useEngineerAnalytics, useEngineerBenchmarks } from "@/hooks/use-api-queries"
import { EngineerLeaderboard } from "@/components/engineers/engineer-leaderboard"
import { BenchmarkTable } from "@/components/engineers/benchmark-table"
import { TableSkeleton } from "@/components/shared/loading-skeleton"
import { EmptyState } from "@/components/shared/empty-state"
import { Button } from "@/components/ui/button"
import { exportToCsv } from "@/lib/csv-export"
import { formatCost } from "@/lib/utils"
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

  const handleExport = () => {
    if (!data) return
    exportToCsv(
      "engineers.csv",
      ["Name", "Sessions", "Tokens", "Estimated Cost", "Success Rate", "Avg Duration"],
      data.engineers.map((e) => [
        e.name,
        e.total_sessions,
        e.total_tokens,
        formatCost(e.estimated_cost),
        e.success_rate != null ? `${(e.success_rate * 100).toFixed(1)}%` : "",
        e.avg_duration != null ? `${Math.round(e.avg_duration)}s` : "",
      ]),
    )
  }

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
