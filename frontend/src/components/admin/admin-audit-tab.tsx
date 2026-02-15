import { useState } from "react"
import { format, parseISO } from "date-fns"
import { cn } from "@/lib/utils"
import { useIngestEvents, useEngineers, useAuditLogs } from "@/hooks/use-api-queries"
import { Badge } from "@/components/ui/badge"
import { TableSkeleton } from "@/components/shared/loading-skeleton"
import { EmptyState } from "@/components/shared/empty-state"

const RESOURCE_TYPES = ["", "engineer", "team", "alert_config"]
const ACTIONS = ["", "create", "update", "deactivate", "rotate_key", "delete"]

type SubTab = "admin" | "ingest"

export function AdminAuditTab() {
  const [subTab, setSubTab] = useState<SubTab>("admin")

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <button
          className={cn(
            "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
            subTab === "admin" ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground hover:text-foreground",
          )}
          onClick={() => setSubTab("admin")}
        >
          Admin Actions
        </button>
        <button
          className={cn(
            "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
            subTab === "ingest" ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground hover:text-foreground",
          )}
          onClick={() => setSubTab("ingest")}
        >
          Ingest Events
        </button>
      </div>

      {subTab === "admin" ? <AdminActionsView /> : <IngestEventsView />}
    </div>
  )
}

function AdminActionsView() {
  const [resourceType, setResourceType] = useState("")
  const [action, setAction] = useState("")

  const { data: logs, isLoading } = useAuditLogs({
    resource_type: resourceType || undefined,
    action: action || undefined,
    limit: 100,
  })

  return (
    <div className="space-y-4">
      <div className="flex gap-3">
        <select
          className="rounded-md border border-input bg-background px-3 py-1.5 text-sm"
          value={resourceType}
          onChange={(e) => setResourceType(e.target.value)}
        >
          <option value="">All resources</option>
          {RESOURCE_TYPES.filter(Boolean).map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
        <select
          className="rounded-md border border-input bg-background px-3 py-1.5 text-sm"
          value={action}
          onChange={(e) => setAction(e.target.value)}
        >
          <option value="">All actions</option>
          {ACTIONS.filter(Boolean).map((a) => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <TableSkeleton />
      ) : !logs || logs.length === 0 ? (
        <EmptyState message="No audit logs found" />
      ) : (
        <div className="rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/50">
                <th className="px-4 py-2 text-left font-medium">Time</th>
                <th className="px-4 py-2 text-left font-medium">Actor</th>
                <th className="px-4 py-2 text-left font-medium">Action</th>
                <th className="px-4 py-2 text-left font-medium">Resource</th>
                <th className="px-4 py-2 text-left font-medium">Details</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id} className="border-b border-border last:border-0">
                  <td className="whitespace-nowrap px-4 py-2 text-muted-foreground">
                    {new Date(log.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-2">
                    <span className="inline-flex items-center gap-1">
                      <span className="rounded bg-muted px-1.5 py-0.5 text-xs">{log.actor_role}</span>
                      {log.actor_id ? <span className="truncate text-xs text-muted-foreground">{log.actor_id.slice(0, 8)}</span> : <span className="text-xs text-muted-foreground">system</span>}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    <span className="rounded bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                      {log.action}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    <span className="text-xs">
                      {log.resource_type}
                      {log.resource_id && <span className="text-muted-foreground"> ({log.resource_id.slice(0, 8)})</span>}
                    </span>
                  </td>
                  <td className="max-w-xs truncate px-4 py-2 text-xs text-muted-foreground">
                    {log.details ? JSON.stringify(log.details) : "-"}
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

function IngestEventsView() {
  const [engineerFilter, setEngineerFilter] = useState("")
  const [statusFilter, setStatusFilter] = useState("")

  const { data: engineers } = useEngineers()
  const { data: events, isLoading } = useIngestEvents({
    engineerId: engineerFilter || undefined,
    status: statusFilter || undefined,
    limit: 100,
  })

  const engineerMap = new Map(engineers?.map((e) => [e.id, e.display_name ?? e.name]) ?? [])

  return (
    <div className="space-y-4">
      <div className="flex gap-3">
        <select
          value={engineerFilter}
          onChange={(e) => setEngineerFilter(e.target.value)}
          className="h-9 rounded-md border border-input bg-background px-3 text-sm"
        >
          <option value="">All engineers</option>
          {engineers?.map((eng) => (
            <option key={eng.id} value={eng.id}>
              {eng.display_name ?? eng.name}
            </option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="h-9 rounded-md border border-input bg-background px-3 text-sm"
        >
          <option value="">All statuses</option>
          <option value="ok">OK</option>
          <option value="error">Error</option>
        </select>
      </div>

      {isLoading ? (
        <TableSkeleton />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/50">
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Time</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Engineer</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Type</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Session</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Status</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Error</th>
              </tr>
            </thead>
            <tbody>
              {events?.map((evt) => (
                <tr key={evt.id} className="border-b border-border last:border-0">
                  <td className="px-4 py-3 text-xs text-muted-foreground">
                    {format(parseISO(evt.created_at), "MMM d, HH:mm:ss")}
                  </td>
                  <td className="px-4 py-3">
                    {engineerMap.get(evt.engineer_id) ?? evt.engineer_id.slice(0, 8)}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">{evt.event_type}</td>
                  <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                    {evt.session_id?.slice(0, 8) ?? "-"}
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={evt.status === "ok" ? "success" : "destructive"}>
                      {evt.status}
                    </Badge>
                  </td>
                  <td className="max-w-48 truncate px-4 py-3 text-xs text-muted-foreground">
                    {evt.error_message ?? "-"}
                  </td>
                </tr>
              ))}
              {events?.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">
                    No ingest events found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
