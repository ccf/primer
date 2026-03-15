import { useNavigate } from "react-router-dom"
import { formatDistanceToNow, parseISO } from "date-fns"
import { Badge } from "@/components/ui/badge"
import { formatDuration } from "@/lib/utils"
import type { SessionResponse } from "@/types/api"

interface RecentSessionsListProps {
  sessions: SessionResponse[]
}

export function RecentSessionsList({ sessions }: RecentSessionsListProps) {
  const navigate = useNavigate()

  const renderAnalysisBadge = (session: SessionResponse) => {
    if (session.has_facets) {
      return <Badge variant="success" className="text-xs">Analyzed</Badge>
    }
    if (session.has_workflow_profile) {
      return <Badge variant="info" className="text-xs">Workflow</Badge>
    }
    return <Badge variant="outline" className="text-xs">Pending</Badge>
  }

  if (sessions.length === 0) {
    return (
      <p className="py-4 text-sm text-muted-foreground">No recent sessions.</p>
    )
  }

  return (
    <div className="space-y-1">
      {sessions.map((s) => (
        <button
          key={s.id}
          onClick={() => navigate(`/sessions/${s.id}`)}
          className="flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm transition-colors hover:bg-accent/5"
        >
          <div className="min-w-0 flex-1">
            <span className="font-medium">
              {s.project_name || s.project_path?.split("/").pop() || "Unknown project"}
            </span>
            <span className="ml-2 text-muted-foreground">
              {s.primary_model?.replace(/^claude-/, "").split("-202")[0] || ""}
            </span>
          </div>
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span>{formatDuration(s.duration_seconds)}</span>
            {s.started_at && (
              <span>{formatDistanceToNow(parseISO(s.started_at), { addSuffix: true })}</span>
            )}
            {renderAnalysisBadge(s)}
          </div>
        </button>
      ))}
    </div>
  )
}
