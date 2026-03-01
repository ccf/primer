import { Link } from "react-router-dom"
import { Users2, ArrowRight } from "lucide-react"
import { useTeams, useEngineers } from "@/hooks/use-api-queries"
import { Card, CardContent } from "@/components/ui/card"
import { PageHeader } from "@/components/shared/page-header"
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
        <PageHeader icon={Users2} title="Teams" description="Team directory and composition" />
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
        <PageHeader icon={Users2} title="Teams" description="Team directory and composition" />
        <EmptyState message="No teams found" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader icon={Users2} title="Teams" description="Team directory and composition" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {teams.map((team, i) => (
          <div
            key={team.id}
            className="animate-stagger-in"
            style={{ animationDelay: `${i * 60}ms` }}
          >
            <Link to={`/teams/${team.id}`} className="group block">
              <Card className="cursor-pointer transition-colors hover:bg-accent/50">
                <CardContent className="p-6">
                  <div className="flex items-start gap-4">
                    <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/8 text-primary transition-transform group-hover:scale-105">
                      <Users2 className="h-6 w-6" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="font-display text-lg">{team.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {engineerCountByTeam[team.id] ?? 0} engineers
                      </p>
                    </div>
                  </div>
                  <div className="mt-4 flex items-center justify-between border-t border-border/40 pt-3">
                    <span className="text-xs text-muted-foreground">View dashboard</span>
                    <ArrowRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
                  </div>
                </CardContent>
              </Card>
            </Link>
          </div>
        ))}
      </div>
    </div>
  )
}
