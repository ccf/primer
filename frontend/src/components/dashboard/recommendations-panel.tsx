import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { RecommendationCard } from "./recommendation-card"
import type { Recommendation } from "@/types/api"
import { EmptyState } from "@/components/shared/empty-state"

interface RecommendationsPanelProps {
  data: Recommendation[]
}

export function RecommendationsPanel({ data }: RecommendationsPanelProps) {
  return (
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
              <RecommendationCard key={i} rec={rec} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
