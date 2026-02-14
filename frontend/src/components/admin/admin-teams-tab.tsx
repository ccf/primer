import { useState } from "react"
import { format, parseISO } from "date-fns"
import { useTeams } from "@/hooks/use-api-queries"
import { useCreateTeam } from "@/hooks/use-api-mutations"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { TableSkeleton } from "@/components/shared/loading-skeleton"

export function AdminTeamsTab() {
  const { data: teams, isLoading } = useTeams()
  const createTeam = useCreateTeam()
  const [newName, setNewName] = useState("")

  if (isLoading) return <TableSkeleton />

  const handleCreate = async () => {
    if (!newName.trim()) return
    await createTeam.mutateAsync(newName.trim())
    setNewName("")
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Teams ({teams?.length ?? 0})</h3>

      <Card>
        <CardHeader><CardTitle>Create Team</CardTitle></CardHeader>
        <CardContent>
          <div className="flex gap-3">
            <input
              placeholder="Team name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCreate()}
              className="h-9 flex-1 rounded-md border border-input bg-background px-3 text-sm"
            />
            <button
              onClick={handleCreate}
              disabled={createTeam.isPending || !newName.trim()}
              className="rounded-md bg-primary px-4 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              Create
            </button>
          </div>
        </CardContent>
      </Card>

      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/50">
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Name</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">ID</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Created</th>
            </tr>
          </thead>
          <tbody>
            {teams?.map((team) => (
              <tr key={team.id} className="border-b border-border last:border-0">
                <td className="px-4 py-3 font-medium">{team.name}</td>
                <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{team.id}</td>
                <td className="px-4 py-3 text-muted-foreground">
                  {format(parseISO(team.created_at), "MMM d, yyyy")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
