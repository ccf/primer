import { useState } from "react"
import { useEngineers, useTeams } from "@/hooks/use-api-queries"
import {
  useDeactivateEngineer,
  useRotateApiKey,
  useUpdateEngineerRole,
  useCreateEngineer,
} from "@/hooks/use-api-mutations"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { TableSkeleton } from "@/components/shared/loading-skeleton"

const roleOptions = ["engineer", "team_lead", "admin"]

export function AdminEngineersTab() {
  const { data: engineers, isLoading } = useEngineers()
  const { data: teams } = useTeams()
  const deactivate = useDeactivateEngineer()
  const rotateKey = useRotateApiKey()
  const updateRole = useUpdateEngineerRole()
  const createEng = useCreateEngineer()

  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState("")
  const [newEmail, setNewEmail] = useState("")
  const [newTeamId, setNewTeamId] = useState("")
  const [newApiKey, setNewApiKey] = useState<string | null>(null)
  const [rotatedKey, setRotatedKey] = useState<Record<string, string>>({})

  if (isLoading) return <TableSkeleton />

  const handleCreate = async () => {
    if (!newName || !newEmail) return
    const result = await createEng.mutateAsync({
      name: newName,
      email: newEmail,
      team_id: newTeamId || undefined,
    })
    setNewApiKey(result.api_key)
    setNewName("")
    setNewEmail("")
    setNewTeamId("")
  }

  const handleRotate = async (engineerId: string) => {
    const result = await rotateKey.mutateAsync(engineerId)
    setRotatedKey((prev) => ({ ...prev, [engineerId]: result.api_key }))
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Engineers ({engineers?.length ?? 0})</h3>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          {showCreate ? "Cancel" : "Create Engineer"}
        </button>
      </div>

      {showCreate && (
        <Card>
          <CardHeader><CardTitle>New Engineer</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-3">
              <input
                placeholder="Name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="h-9 rounded-md border border-input bg-background px-3 text-sm"
              />
              <input
                placeholder="Email"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                className="h-9 rounded-md border border-input bg-background px-3 text-sm"
              />
              <select
                value={newTeamId}
                onChange={(e) => setNewTeamId(e.target.value)}
                className="h-9 rounded-md border border-input bg-background px-3 text-sm"
              >
                <option value="">No team</option>
                {teams?.map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </div>
            <button
              onClick={handleCreate}
              disabled={createEng.isPending}
              className="rounded-md bg-primary px-4 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              Create
            </button>
            {newApiKey && (
              <div className="rounded-md bg-green-50 p-3 dark:bg-green-900/20">
                <p className="text-sm font-medium text-green-700 dark:text-green-400">API Key (copy now):</p>
                <code className="mt-1 block break-all text-xs">{newApiKey}</code>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/50">
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Name</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Email</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Role</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Status</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Actions</th>
            </tr>
          </thead>
          <tbody>
            {engineers?.map((eng) => (
              <tr key={eng.id} className="border-b border-border last:border-0">
                <td className="px-4 py-3 font-medium">{eng.display_name ?? eng.name}</td>
                <td className="px-4 py-3 text-muted-foreground">{eng.email}</td>
                <td className="px-4 py-3">
                  <select
                    value={eng.role}
                    onChange={(e) =>
                      updateRole.mutate({ engineerId: eng.id, role: e.target.value })
                    }
                    className="h-7 rounded border border-input bg-background px-2 text-xs"
                  >
                    {roleOptions.map((r) => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </select>
                </td>
                <td className="px-4 py-3">
                  <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${eng.is_active ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"}`}>
                    {eng.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleRotate(eng.id)}
                      className="rounded px-2 py-1 text-xs text-muted-foreground hover:bg-accent hover:text-foreground"
                    >
                      Rotate Key
                    </button>
                    {eng.is_active && (
                      <button
                        onClick={() => deactivate.mutate(eng.id)}
                        className="rounded px-2 py-1 text-xs text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
                      >
                        Deactivate
                      </button>
                    )}
                  </div>
                  {rotatedKey[eng.id] && (
                    <div className="mt-1 rounded bg-green-50 p-1.5 dark:bg-green-900/20">
                      <code className="break-all text-[10px]">{rotatedKey[eng.id]}</code>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
