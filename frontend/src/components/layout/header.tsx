import type { TeamResponse } from "@/types/api"
import { useTeams } from "@/hooks/use-api-queries"
import { clearApiKey } from "@/lib/api"
import { LogOut } from "lucide-react"

interface HeaderProps {
  teamId: string | null
  onTeamChange: (id: string | null) => void
}

export function Header({ teamId, onTeamChange }: HeaderProps) {
  const { data: teams } = useTeams()

  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-card px-6">
      <div />
      <div className="flex items-center gap-3">
        <select
          value={teamId ?? ""}
          onChange={(e) => onTeamChange(e.target.value || null)}
          className="h-8 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
        >
          <option value="">All teams</option>
          {teams?.map((t: TeamResponse) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
        <button
          onClick={() => {
            clearApiKey()
            window.location.reload()
          }}
          className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground"
          title="Sign out"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </header>
  )
}
