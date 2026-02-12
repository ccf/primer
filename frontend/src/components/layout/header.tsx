import type { TeamResponse } from "@/types/api"
import { useTeams } from "@/hooks/use-api-queries"
import { useAuth } from "@/lib/auth-context"
import { clearApiKey, getApiKey } from "@/lib/api"
import { LogOut } from "lucide-react"

interface HeaderProps {
  teamId: string | null
  onTeamChange: (id: string | null) => void
}

const roleBadgeColors: Record<string, string> = {
  admin: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  team_lead: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  engineer: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
}

const roleLabels: Record<string, string> = {
  admin: "Admin",
  team_lead: "Team Lead",
  engineer: "Engineer",
}

export function Header({ teamId, onTeamChange }: HeaderProps) {
  const { data: teams } = useTeams()
  const { user, logout } = useAuth()
  const isApiKeyUser = !user && !!getApiKey()
  const role = user?.role ?? (isApiKeyUser ? "admin" : "engineer")
  const showTeamFilter = role === "admin"

  const handleLogout = async () => {
    if (user) {
      await logout()
      window.location.reload()
    } else {
      clearApiKey()
      window.location.reload()
    }
  }

  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-card px-6">
      <div />
      <div className="flex items-center gap-3">
        {showTeamFilter && (
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
        )}

        {user && (
          <div className="flex items-center gap-2">
            <span
              className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${roleBadgeColors[role] ?? roleBadgeColors.engineer}`}
            >
              {roleLabels[role] ?? role}
            </span>
            {user.avatar_url ? (
              <img
                src={user.avatar_url}
                alt={user.display_name ?? user.name}
                className="h-7 w-7 rounded-full"
              />
            ) : (
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-muted text-xs font-medium">
                {(user.display_name ?? user.name).charAt(0).toUpperCase()}
              </div>
            )}
            <span className="text-sm font-medium">
              {user.display_name ?? user.name}
            </span>
          </div>
        )}

        <button
          onClick={handleLogout}
          className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground"
          title="Sign out"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </header>
  )
}
