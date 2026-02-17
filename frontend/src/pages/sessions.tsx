import { useAuth } from "@/lib/auth-context"
import { useFriction } from "@/hooks/use-api-queries"
import { SessionBrowser } from "@/components/sessions/session-browser"
import { FrictionList } from "@/components/analytics/friction-list"
import { ChartSkeleton } from "@/components/shared/loading-skeleton"
import type { DateRange } from "@/components/layout/date-range-picker"

interface SessionsPageProps {
  teamId: string | null
  dateRange: DateRange | null
}

export function SessionsPage({ teamId, dateRange }: SessionsPageProps) {
  const { user } = useAuth()
  const role = user?.role ?? "admin"
  const startDate = dateRange?.startDate
  const endDate = dateRange?.endDate
  const { data: friction, isLoading: loadingFriction } = useFriction(teamId, startDate, endDate)

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">
        {role === "engineer" ? "My Sessions" : "Sessions"}
      </h1>

      <SessionBrowser
        teamId={teamId}
        dateRange={dateRange}
        showEngineerFilter={role === "admin"}
      />

      {loadingFriction ? <ChartSkeleton /> : friction && <FrictionList data={friction} />}
    </div>
  )
}
