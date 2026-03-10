import { useTimeToTeamAverage } from "@/hooks/use-api-queries"
import { TrajectorySparklines } from "@/components/engineer-profile/trajectory-sparklines"
import { LearningPathCards } from "@/components/growth/learning-path-cards"
import { TimeToTeamAverage } from "@/components/growth/time-to-team-average"
import { WorkflowPlaybookCards } from "@/components/growth/workflow-playbook-cards"
import { ChartSkeleton } from "@/components/shared/loading-skeleton"
import type { EngineerProfileResponse } from "@/types/api"

interface ProfileGrowthTabProps {
  profile: EngineerProfileResponse
  teamId: string | null
  startDate?: string
  endDate?: string
}

export function ProfileGrowthTab({ profile, teamId, startDate, endDate }: ProfileGrowthTabProps) {
  const { data: timeToAvg, isLoading: loadingTimeToAvg } = useTimeToTeamAverage(teamId, startDate, endDate)

  return (
    <div className="space-y-6">
      <div>
        <h3 className="mb-3 text-sm font-medium">Weekly Trajectory</h3>
        <TrajectorySparklines data={profile.weekly_trajectory} />
      </div>

      {profile.learning_paths.length > 0 && (
        <div>
          <h3 className="mb-3 text-sm font-medium">Learning Paths</h3>
          <LearningPathCards paths={profile.learning_paths} />
        </div>
      )}

      {profile.workflow_playbooks.length > 0 && (
        <div>
          <h3 className="mb-3 text-sm font-medium">Workflow Playbooks</h3>
          <WorkflowPlaybookCards playbooks={profile.workflow_playbooks} />
        </div>
      )}

      {loadingTimeToAvg ? (
        <ChartSkeleton />
      ) : (
        timeToAvg && (
          <div>
            <h3 className="mb-3 text-sm font-medium">Time to Team Average</h3>
            <TimeToTeamAverage teamId={teamId} startDate={startDate} endDate={endDate} />
          </div>
        )
      )}
    </div>
  )
}
