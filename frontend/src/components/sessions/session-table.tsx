import { useEffect, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { format, parseISO } from "date-fns"
import { Badge } from "@/components/ui/badge"
import type { SessionResponse } from "@/types/api"
import { formatDuration, formatTokens, cn } from "@/lib/utils"

interface SessionTableProps {
  sessions: SessionResponse[]
  selectedIndex?: number
}

export function SessionTable({ sessions, selectedIndex = -1 }: SessionTableProps) {
  const navigate = useNavigate()
  const selectedRef = useRef<HTMLTableRowElement>(null)

  useEffect(() => {
    if (selectedIndex >= 0 && selectedRef.current) {
      selectedRef.current.scrollIntoView({ block: "nearest" })
    }
  }, [selectedIndex])

  return (
    <div className="overflow-x-auto rounded-xl border border-border/60">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/60">
            <th className="px-4 py-3 text-left font-medium text-muted-foreground">Project</th>
            <th className="px-4 py-3 text-left font-medium text-muted-foreground">Model</th>
            <th className="px-4 py-3 text-left font-medium text-muted-foreground">Started</th>
            <th className="px-4 py-3 text-right font-medium text-muted-foreground">Duration</th>
            <th className="px-4 py-3 text-right font-medium text-muted-foreground">Messages</th>
            <th className="px-4 py-3 text-right font-medium text-muted-foreground">Tools</th>
            <th className="px-4 py-3 text-right font-medium text-muted-foreground">Tokens</th>
            <th className="px-4 py-3 text-left font-medium text-muted-foreground">Facets</th>
          </tr>
        </thead>
        <tbody>
          {sessions.map((s, i) => (
            <tr
              key={s.id}
              ref={i === selectedIndex ? selectedRef : undefined}
              onClick={() => navigate(`/sessions/${s.id}`)}
              className={cn(
                "cursor-pointer border-b border-border/40 transition-colors even:bg-muted/15 hover:bg-accent/50 last:border-0",
                i === selectedIndex && "ring-2 ring-ring ring-inset",
              )}
            >
              <td className="px-4 py-3 font-medium">{s.project_name || s.project_path?.split("/").pop() || "-"}</td>
              <td className="px-4 py-3 text-muted-foreground">
                {s.primary_model?.replace(/^claude-/, "").split("-202")[0] || "-"}
              </td>
              <td className="px-4 py-3 text-muted-foreground">
                {s.started_at ? format(parseISO(s.started_at), "MMM d, HH:mm") : "-"}
              </td>
              <td className="px-4 py-3 text-right">{formatDuration(s.duration_seconds)}</td>
              <td className="px-4 py-3 text-right">{s.message_count}</td>
              <td className="px-4 py-3 text-right">{s.tool_call_count}</td>
              <td className="px-4 py-3 text-right">{formatTokens(s.input_tokens + s.output_tokens)}</td>
              <td className="px-4 py-3">
                {s.has_facets ? (
                  <Badge variant="success">Yes</Badge>
                ) : (
                  <Badge variant="outline">No</Badge>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
