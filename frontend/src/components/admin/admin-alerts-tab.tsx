import { useState } from "react"
import { Trash2 } from "lucide-react"
import { useAlertConfigs, useResolvedThresholds, useTeams } from "@/hooks/use-api-queries"
import { useCreateAlertConfig, useDeleteAlertConfig, useUpdateAlertConfig } from "@/hooks/use-api-mutations"
import { Button } from "@/components/ui/button"
import { TableSkeleton } from "@/components/shared/loading-skeleton"

const ALERT_TYPES = [
  { value: "friction_spike", label: "Friction Spike" },
  { value: "usage_drop", label: "Usage Drop" },
  { value: "cost_spike_warning", label: "Cost Spike (Warning)" },
  { value: "cost_spike_critical", label: "Cost Spike (Critical)" },
  { value: "success_rate_drop", label: "Success Rate Drop" },
]

export function AdminAlertsTab() {
  const { data: configs, isLoading } = useAlertConfigs()
  const { data: thresholds } = useResolvedThresholds()
  const { data: teams } = useTeams()
  const createMutation = useCreateAlertConfig()
  const updateMutation = useUpdateAlertConfig()
  const deleteMutation = useDeleteAlertConfig()

  const [newType, setNewType] = useState(ALERT_TYPES[0].value)
  const [newThreshold, setNewThreshold] = useState("")
  const [newTeamId, setNewTeamId] = useState("")

  const handleCreate = () => {
    const threshold = parseFloat(newThreshold)
    if (isNaN(threshold)) return
    createMutation.mutate({
      team_id: newTeamId || null,
      alert_type: newType,
      threshold,
    })
    setNewThreshold("")
  }

  if (isLoading) return <TableSkeleton />

  return (
    <div className="space-y-6">
      {/* Add Override */}
      <div className="rounded-lg border border-border p-4">
        <h3 className="mb-3 text-sm font-semibold">Add Override</h3>
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">Team (optional)</label>
            <select
              className="rounded-md border border-input bg-background px-3 py-1.5 text-sm"
              value={newTeamId}
              onChange={(e) => setNewTeamId(e.target.value)}
            >
              <option value="">Global</option>
              {teams?.map((t) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">Alert Type</label>
            <select
              className="rounded-md border border-input bg-background px-3 py-1.5 text-sm"
              value={newType}
              onChange={(e) => setNewType(e.target.value)}
            >
              {ALERT_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">Threshold</label>
            <input
              type="number"
              step="0.1"
              className="w-24 rounded-md border border-input bg-background px-3 py-1.5 text-sm"
              value={newThreshold}
              onChange={(e) => setNewThreshold(e.target.value)}
              placeholder="e.g. 2.0"
            />
          </div>
          <Button size="sm" onClick={handleCreate} disabled={createMutation.isPending || !newThreshold}>
            Add
          </Button>
        </div>
      </div>

      {/* Overrides Table */}
      {configs && configs.length > 0 && (
        <div className="rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/50">
                <th className="px-4 py-2 text-left font-medium">Scope</th>
                <th className="px-4 py-2 text-left font-medium">Alert Type</th>
                <th className="px-4 py-2 text-left font-medium">Threshold</th>
                <th className="px-4 py-2 text-left font-medium">Enabled</th>
                <th className="px-4 py-2 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {configs.map((c) => (
                <tr key={c.id} className="border-b border-border last:border-0">
                  <td className="px-4 py-2">
                    {c.team_id ? teams?.find((t) => t.id === c.team_id)?.name ?? c.team_id : "Global"}
                  </td>
                  <td className="px-4 py-2">
                    {ALERT_TYPES.find((t) => t.value === c.alert_type)?.label ?? c.alert_type}
                  </td>
                  <td className="px-4 py-2">{c.threshold}</td>
                  <td className="px-4 py-2">
                    <button
                      className={`rounded px-2 py-0.5 text-xs font-medium ${c.enabled ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200" : "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"}`}
                      onClick={() => updateMutation.mutate({ id: c.id, enabled: !c.enabled })}
                    >
                      {c.enabled ? "Yes" : "No"}
                    </button>
                  </td>
                  <td className="px-4 py-2 text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => deleteMutation.mutate(c.id)}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Effective Defaults */}
      {thresholds && (
        <div className="rounded-lg border border-border p-4">
          <h3 className="mb-3 text-sm font-semibold">Effective Defaults</h3>
          <dl className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-muted-foreground">Friction Spike</dt>
              <dd className="font-medium">{thresholds.friction_spike_multiplier}x</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Usage Drop</dt>
              <dd className="font-medium">{thresholds.usage_drop_ratio}x</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Cost Warning</dt>
              <dd className="font-medium">{thresholds.cost_spike_warning}x</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Cost Critical</dt>
              <dd className="font-medium">{thresholds.cost_spike_critical}x</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Success Rate Drop</dt>
              <dd className="font-medium">{thresholds.success_rate_drop_pp}pp</dd>
            </div>
          </dl>
        </div>
      )}
    </div>
  )
}
