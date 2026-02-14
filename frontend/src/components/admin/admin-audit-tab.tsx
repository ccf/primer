import { useState } from "react"
import { format, parseISO } from "date-fns"
import { useIngestEvents, useEngineers } from "@/hooks/use-api-queries"
import { Badge } from "@/components/ui/badge"
import { TableSkeleton } from "@/components/shared/loading-skeleton"

export function AdminAuditTab() {
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
      <h3 className="text-lg font-semibold">Ingest Audit Log</h3>

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
