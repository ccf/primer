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
}

export function RecommendationsPanel({
  data,
  teamId,
  engineerId,
  projectName,
  startDate,
  endDate,
  defaultOwnerEngineerId,
}: RecommendationsPanelProps) {
  const [selectedRecommendation, setSelectedRecommendation] = useState<Recommendation | null>(null)

  return (
    <>
      <Card className="col-span-full">
        <CardHeader>
          <CardTitle className="text-sm font-medium">Recommendations</CardTitle>
        </CardHeader>
        <CardContent>
          {data.length === 0 ? (
            <EmptyState message="No recommendations — everything looks good!" />
          ) : (
            <div className="space-y-3">
              {data.map((rec, i) => (
                <RecommendationCard
                  key={i}
                  rec={rec}
                  onCreateIntervention={() => setSelectedRecommendation(rec)}
                />
              ))}
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
