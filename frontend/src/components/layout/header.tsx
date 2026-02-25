import type { TeamResponse } from "@/types/api"
import { useTeams } from "@/hooks/use-api-queries"
import { useAuth } from "@/lib/auth-context"
import { getApiKey } from "@/lib/api"
import { getEffectiveRole } from "@/lib/role-utils"
import { PanelLeft } from "lucide-react"
import { DateRangePicker, type DateRange } from "./date-range-picker"
import { AlertBell } from "./alert-bell"

interface HeaderProps {
  teamId: string | null
  onTeamChange: (id: string | null) => void
  dateRange: DateRange | null
  onDateRangeChange: (range: DateRange | null) => void
  sidebarCollapsed: boolean
  onToggleSidebar: () => void
}

export function Header({
  teamId,
  onTeamChange,
  dateRange,
  onDateRangeChange,
  sidebarCollapsed,
  onToggleSidebar,
}: HeaderProps) {
  const { data: teams } = useTeams()
  const { user } = useAuth()
  const isApiKeyUser = !user && !!getApiKey()
  const role = user?.role ?? (isApiKeyUser ? "admin" : "engineer")
  const showTeamFilter = getEffectiveRole(role) === "leadership"

  return (
    <header className="flex h-12 items-center justify-between border-b border-border bg-card px-4">
      <div className="flex items-center gap-3">
        {sidebarCollapsed && (
          <button
            onClick={onToggleSidebar}
            className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
            title="Expand sidebar"
          >
            <PanelLeft className="h-4 w-4" />
          </button>
        )}

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

        <DateRangePicker value={dateRange} onChange={onDateRangeChange} />
      </div>

      <div className="flex items-center gap-3">
        <AlertBell />
      </div>
    </header>
  )
}
