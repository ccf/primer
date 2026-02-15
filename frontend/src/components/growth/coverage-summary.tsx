import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { LearningPathsResponse } from "@/types/api"

interface CoverageSummaryProps {
  data: LearningPathsResponse
}

export function CoverageSummary({ data }: CoverageSummaryProps) {
  const totalRecs = data.engineer_paths.reduce((sum, p) => sum + p.recommendations.length, 0)
  const avgCoverage =
    data.engineer_paths.length > 0
      ? data.engineer_paths.reduce((sum, p) => sum + p.coverage_score, 0) / data.engineer_paths.length
      : 0

  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">Engineers Analyzed</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{data.engineer_paths.length}</div>
          <p className="text-xs text-muted-foreground">{data.sessions_analyzed} sessions</p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">Avg Coverage</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{(avgCoverage * 100).toFixed(0)}%</div>
          <p className="text-xs text-muted-foreground">of team skill universe</p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">Recommendations</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{totalRecs}</div>
          <p className="text-xs text-muted-foreground">learning opportunities</p>
        </CardContent>
      </Card>
    </div>
  )
}
