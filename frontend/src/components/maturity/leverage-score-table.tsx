import { Card, CardContent, CardHeader } from "@/components/ui/card"
import type { EngineerLeverageProfile } from "@/types/api"

interface LeverageScoreTableProps {
  data: EngineerLeverageProfile[]
}

function ScoreBar({ score }: { score: number }) {
  const color =
    score >= 60 ? "bg-emerald-500" : score >= 30 ? "bg-amber-500" : "bg-red-400"
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-20 rounded-full bg-muted">
        <div
          className={`h-2 rounded-full ${color}`}
          style={{ width: `${Math.min(score, 100)}%` }}
        />
      </div>
      <span className="text-xs font-medium">{score.toFixed(1)}</span>
    </div>
  )
}

export function LeverageScoreTable({ data }: LeverageScoreTableProps) {
  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <h3 className="text-sm font-medium">Engineer Leverage Scores</h3>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No engineer data available.</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <h3 className="text-sm font-medium">Engineer Leverage Scores</h3>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="pb-2 font-medium">Engineer</th>
                <th className="pb-2 font-medium">Score</th>
                <th className="pb-2 text-right font-medium">Tool Calls</th>
                <th className="pb-2 text-right font-medium">Orch.</th>
                <th className="pb-2 text-right font-medium">Skills</th>
                <th className="pb-2 font-medium">Top Agents</th>
              </tr>
            </thead>
            <tbody>
              {data.map((profile) => (
                <tr key={profile.engineer_id} className="border-b border-border/40">
                  <td className="py-2 font-medium">{profile.name}</td>
                  <td className="py-2">
                    <ScoreBar score={profile.leverage_score} />
                  </td>
                  <td className="py-2 text-right">{profile.total_tool_calls.toLocaleString()}</td>
                  <td className="py-2 text-right">{profile.orchestration_calls}</td>
                  <td className="py-2 text-right">{profile.skill_calls}</td>
                  <td className="py-2">
                    <span className="text-xs text-muted-foreground">
                      {[...profile.top_agents, ...profile.top_skills].slice(0, 3).join(", ") || "—"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}
