import { format, parseISO } from "date-fns"
import type { EngineerResponse, TeamResponse } from "@/types/api"

interface EngineerTableProps {
  engineers: EngineerResponse[]
  teams: TeamResponse[]
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

export function EngineerTable({ engineers, teams }: EngineerTableProps) {
  const teamMap = new Map(teams.map((t) => [t.id, t.name]))

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/50">
            <th className="px-4 py-3 text-left font-medium text-muted-foreground">Engineer</th>
            <th className="px-4 py-3 text-left font-medium text-muted-foreground">Email</th>
            <th className="px-4 py-3 text-left font-medium text-muted-foreground">Role</th>
            <th className="px-4 py-3 text-left font-medium text-muted-foreground">Team</th>
            <th className="px-4 py-3 text-left font-medium text-muted-foreground">Joined</th>
          </tr>
        </thead>
        <tbody>
          {engineers.map((eng) => (
            <tr key={eng.id} className="border-b border-border last:border-0">
              <td className="px-4 py-3">
                <div className="flex items-center gap-2">
                  {eng.avatar_url ? (
                    <img
                      src={eng.avatar_url}
                      alt={eng.display_name ?? eng.name}
                      className="h-7 w-7 rounded-full"
                    />
                  ) : (
                    <div className="flex h-7 w-7 items-center justify-center rounded-full bg-muted text-xs font-medium">
                      {(eng.display_name ?? eng.name).charAt(0).toUpperCase()}
                    </div>
                  )}
                  <div>
                    <p className="font-medium">{eng.display_name ?? eng.name}</p>
                    {eng.github_username && (
                      <p className="text-xs text-muted-foreground">@{eng.github_username}</p>
                    )}
                  </div>
                </div>
              </td>
              <td className="px-4 py-3 text-muted-foreground">{eng.email}</td>
              <td className="px-4 py-3">
                <span
                  className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${roleBadgeColors[eng.role] ?? roleBadgeColors.engineer}`}
                >
                  {roleLabels[eng.role] ?? eng.role}
                </span>
              </td>
              <td className="px-4 py-3">{eng.team_id ? teamMap.get(eng.team_id) ?? "-" : "-"}</td>
              <td className="px-4 py-3 text-muted-foreground">
                {format(parseISO(eng.created_at), "MMM d, yyyy")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
