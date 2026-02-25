import { Link } from "react-router-dom"
import { Users2 } from "lucide-react"
import { useTeams, useEngineers } from "@/hooks/use-api-queries"
import { Card, CardContent } from "@/components/ui/card"
import { CardSkeleton } from "@/components/shared/loading-skeleton"
import { EmptyState } from "@/components/shared/empty-state"

export function TeamsPage() {
  const { data: teams, isLoading: loadingTeams } = useTeams()
  const { data: engineers } = useEngineers()

  const engineerCountByTeam = (engineers ?? []).reduce<Record<string, number>>((acc, eng) => {
    if (eng.team_id) {
      acc[eng.team_id] = (acc[eng.team_id] ?? 0) + 1
    }
    return acc
  }, {})

  if (loadingTeams) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-semibold">Teams</h1>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      </div>
    )
  }

  if (!teams || teams.length === 0) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-semibold">Teams</h1>
        <EmptyState message="No teams found" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Teams</h1>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {teams.map((team) => (
          <Link key={team.id} to={`/teams/${team.id}`}>
            <Card className="cursor-pointer transition-colors hover:bg-accent/50">
              <CardContent className="flex items-center gap-4 p-6">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Users2 className="h-5 w-5" />
                </div>
                <div>
                  <p className="font-semibold">{team.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {engineerCountByTeam[team.id] ?? 0} engineers
                  </p>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  )
}
