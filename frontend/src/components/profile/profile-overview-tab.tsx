import { useActivityHeatmap, useSessions, useRecommendations } from "@/hooks/use-api-queries"
import { ActivityHeatmap } from "@/components/dashboard/activity-heatmap"
import { RecommendationsPanel } from "@/components/dashboard/recommendations-panel"
import { RecentSessionsList } from "./recent-sessions-list"
import { ChartSkeleton, CardSkeleton } from "@/components/shared/loading-skeleton"

interface ProfileOverviewTabProps {
  engineerId: string
  teamId: string | null
  startDate?: string
  endDate?: string
}

export function ProfileOverviewTab({ engineerId, teamId, startDate, endDate }: ProfileOverviewTabProps) {
  const { data: heatmap, isLoading: loadingHeatmap } = useActivityHeatmap(teamId, startDate, endDate)
  const { data: sessions, isLoading: loadingSessions } = useSessions({
    teamId,
    engineerId,
    startDate,
    endDate,
    limit: 10,
  })
  const { data: recs, isLoading: loadingRecs } = useRecommendations(teamId, startDate, endDate)

  return (
    <div className="space-y-6">
      {loadingHeatmap ? (
        <ChartSkeleton />
      ) : (
        heatmap && heatmap.cells.length > 0 && <ActivityHeatmap data={heatmap} />
      )}

      <div>
        <h3 className="mb-2 text-sm font-medium">Recent Sessions</h3>
        {loadingSessions ? (
          <CardSkeleton />
        ) : (
          <RecentSessionsList sessions={sessions ?? []} />
        )}
      </div>

      {loadingRecs ? (
        <ChartSkeleton />
      ) : (
        recs && recs.length > 0 && <RecommendationsPanel data={recs} />
      )}
    </div>
  )
}
