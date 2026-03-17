import { usePersonalizedTips } from "@/hooks/use-api-queries"
import { FrictionTab } from "@/components/engineer-profile/friction-tab"
import { StrengthsTab } from "@/components/engineer-profile/strengths-tab"
import { PersonalizedTipsList } from "@/components/insights/personalized-tips-list"
import { CardSkeleton } from "@/components/shared/loading-skeleton"
import type { EngineerProfileResponse } from "@/types/api"

interface ProfileInsightsTabProps {
  profile: EngineerProfileResponse
  teamId: string | null
  startDate?: string
  endDate?: string
}

export function ProfileInsightsTab({ profile, teamId, startDate, endDate }: ProfileInsightsTabProps) {
  const { data: tips, isLoading: loadingTips } = usePersonalizedTips(teamId, startDate, endDate)

  return (
    <div className="space-y-8">
      <div>
        <h3 className="mb-3 text-sm font-medium">Strengths & Skills</h3>
        <StrengthsTab
          strengths={profile.strengths}
          learningPaths={profile.learning_paths}
          toolRecommendations={profile.tool_recommendations}
        />
      </div>

      <div>
        <h3 className="mb-3 text-sm font-medium">Friction & Config</h3>
        <FrictionTab friction={profile.friction} configSuggestions={profile.config_suggestions} />
      </div>

      <div>
        <h3 className="mb-3 text-sm font-medium">Personalized Tips</h3>
        {loadingTips ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <CardSkeleton key={i} />
            ))}
          </div>
        ) : (
          <PersonalizedTipsList
            tips={tips?.tips ?? []}
            sessionsAnalyzed={tips?.sessions_analyzed ?? 0}
          />
        )}
      </div>
    </div>
  )
}
