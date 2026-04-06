import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { InterventionFormModal } from "@/components/interventions/intervention-form-modal"
import { RecommendationCard } from "./recommendation-card"
import type { Recommendation } from "@/types/api"
import { EmptyState } from "@/components/shared/empty-state"

interface RecommendationsPanelProps {
  data: Recommendation[]
  teamId: string | null
  engineerId?: string | null
  projectName?: string | null
  startDate?: string
  endDate?: string
  defaultOwnerEngineerId?: string | null
  limit?: number
}

export function RecommendationsPanel({
  data,
  teamId,
  engineerId,
  projectName,
  startDate,
  endDate,
  defaultOwnerEngineerId,
  limit,
}: RecommendationsPanelProps) {
  const [selectedRecommendation, setSelectedRecommendation] = useState<Recommendation | null>(null)
  const [showAll, setShowAll] = useState(false)

  const visibleData = limit && !showAll ? data.slice(0, limit) : data
  const hasMore = limit != null && data.length > limit && !showAll

  return (
    <>
      <Card className="col-span-full">
        <CardHeader>
          <CardTitle className="text-sm font-medium">Recommendations</CardTitle>
        </CardHeader>
        <CardContent>
          {data.length === 0 ? (
            <EmptyState
              title="No recommendations right now"
              description="Recommendations appear when Primer detects friction patterns, cost opportunities, or workflow improvements worth acting on."
            />
          ) : (
            <div className="space-y-3">
              {visibleData.map((rec, i) => (
                <RecommendationCard
                  key={i}
                  rec={rec}
                  onCreateIntervention={() => setSelectedRecommendation(rec)}
                />
              ))}
              {hasMore && (
                <button
                  type="button"
                  onClick={() => setShowAll(true)}
                  className="text-xs text-primary hover:underline"
                >
                  Show all {data.length} recommendations
                </button>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <InterventionFormModal
        open={selectedRecommendation != null}
        onClose={() => setSelectedRecommendation(null)}
        recommendation={selectedRecommendation}
        teamId={teamId}
        engineerId={engineerId}
        projectName={projectName}
        startDate={startDate}
        endDate={endDate}
        defaultOwnerEngineerId={defaultOwnerEngineerId}
      />
    </>
  )
}
