import { useState, useMemo } from "react"
import { useAuth } from "@/lib/auth-context"
import { getApiKey } from "@/lib/api"
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
  const { data: benchmarks } = useEngineerBenchmarks(teamId, startDate, endDate, canBenchmark)
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

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-semibold">Engineers</h1>
        <TableSkeleton />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Engineers</h1>

      {!data || data.engineers.length === 0 ? (
        <EmptyState message="No engineers found" />
      ) : (
        <EngineerLeaderboard
          engineers={engineers}
          benchmark={benchmarks?.benchmark}
          onSortChange={setSortBy}
          sortBy={sortBy}
        />
      )}
    </div>
  )
}
