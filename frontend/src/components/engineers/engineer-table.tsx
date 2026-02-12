import { format, parseISO } from "date-fns"
import type { EngineerResponse, TeamResponse } from "@/types/api"

interface EngineerTableProps {
  engineers: EngineerResponse[]
  teams: TeamResponse[]
}

export function EngineerTable({ engineers, teams }: EngineerTableProps) {
  const teamMap = new Map(teams.map((t) => [t.id, t.name]))

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/50">
            <th className="px-4 py-3 text-left font-medium text-muted-foreground">Name</th>
            <th className="px-4 py-3 text-left font-medium text-muted-foreground">Email</th>
            <th className="px-4 py-3 text-left font-medium text-muted-foreground">Team</th>
            <th className="px-4 py-3 text-left font-medium text-muted-foreground">Joined</th>
          </tr>
        </thead>
        <tbody>
          {engineers.map((eng) => (
            <tr key={eng.id} className="border-b border-border last:border-0">
              <td className="px-4 py-3 font-medium">{eng.name}</td>
              <td className="px-4 py-3 text-muted-foreground">{eng.email}</td>
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
