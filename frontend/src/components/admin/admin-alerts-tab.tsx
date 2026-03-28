import { useState } from "react"
import { Trash2 } from "lucide-react"
import { useAlertConfigs, useResolvedAlertPolicy, useTeams } from "@/hooks/use-api-queries"
import { useCreateAlertConfig, useDeleteAlertConfig, useUpdateAlertConfig } from "@/hooks/use-api-mutations"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
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
  const { data: teams } = useTeams()
  const [policyTeamId, setPolicyTeamId] = useState("")
  const { data: policy } = useResolvedAlertPolicy(policyTeamId || null)
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

  const sourceLabel = (source: string) => source.replaceAll("_", " ")
  const formatThreshold = (threshold: number, unitLabel: string) => {
    if (unitLabel === "percentage points") return `${threshold}pp`
    return `${threshold} ${unitLabel}`
  }

  return (
    <div className="space-y-6">
      {policy && (
        <Card>
          <CardHeader className="pb-4">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <CardTitle>Effective Policy</CardTitle>
                <p className="text-sm text-muted-foreground">
                  Resolved alert behavior for the selected scope, including overrides and disabled states.
                </p>
              </div>
              <div>
                <label className="mb-1 block text-xs text-muted-foreground">Inspect team</label>
                <select
                  className="rounded-md border border-input bg-background px-3 py-1.5 text-sm"
                  value={policyTeamId}
                  onChange={(e) => setPolicyTeamId(e.target.value)}
                >
                  <option value="">Global</option>
                  {teams?.map((t) => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-2 text-sm text-muted-foreground">
              <Badge variant={policy.notifications_enabled ? "success" : "outline"}>
                {policy.notifications_enabled ? "Slack enabled" : "Slack disabled"}
              </Badge>
              <Badge variant={policy.webhook_configured ? "success" : "outline"}>
                {policy.webhook_configured ? "Webhook configured" : "Webhook missing"}
              </Badge>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-muted/50 text-left">
                    <th className="px-4 py-2 font-medium">Alert</th>
                    <th className="px-4 py-2 font-medium">Effective</th>
                    <th className="px-4 py-2 font-medium">Source</th>
                    <th className="px-4 py-2 font-medium">Window</th>
                    <th className="px-4 py-2 font-medium">Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {policy.policies.map((item) => (
                    <tr key={item.alert_type} className="border-b border-border last:border-0">
                      <td className="px-4 py-3 align-top">
                        <div className="space-y-1">
                          <div className="font-medium">{item.label}</div>
                          <div className="text-xs text-muted-foreground">{item.description}</div>
                        </div>
                      </td>
                      <td className="px-4 py-3 align-top">
                        <div className="space-y-1">
                          <Badge variant={item.effective_enabled ? "success" : "outline"}>
                            {item.effective_enabled ? "Enabled" : "Disabled"}
                          </Badge>
                          <div className="font-medium">
                            {formatThreshold(item.effective_threshold, item.unit_label)}
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 align-top">
                        <Badge variant="outline">{sourceLabel(item.source)}</Badge>
                      </td>
                      <td className="px-4 py-3 align-top text-muted-foreground">
                        {item.detector_window}
                      </td>
                      <td className="px-4 py-3 align-top text-xs text-muted-foreground">
                        Default {formatThreshold(item.default_threshold, item.unit_label)}
                        {item.global_override_threshold != null && (
                          <div>
                            Global override: {formatThreshold(item.global_override_threshold, item.unit_label)}
                            {item.global_override_enabled === false ? " (disabled)" : ""}
                          </div>
                        )}
                        {item.team_override_threshold != null && (
                          <div>
                            Team override: {formatThreshold(item.team_override_threshold, item.unit_label)}
                            {item.team_override_enabled === false ? " (disabled)" : ""}
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

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

    </div>
  )
}
