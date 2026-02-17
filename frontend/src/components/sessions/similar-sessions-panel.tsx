import { Link } from "react-router-dom"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { CardSkeleton } from "@/components/shared/loading-skeleton"
import { useSimilarSessions } from "@/hooks/use-api-queries"
import { formatDuration } from "@/lib/utils"
import type { SimilarSession } from "@/types/api"

interface SimilarSessionsPanelProps {
  sessionId: string
}

const outcomeBadge: Record<string, { variant: "success" | "destructive" | "warning" | "secondary"; label: string }> = {
  success: { variant: "success", label: "Success" },
  failure: { variant: "destructive", label: "Failure" },
  partial: { variant: "warning", label: "Partial" },
  abandoned: { variant: "secondary", label: "Abandoned" },
}

function SessionRow({ session }: { session: SimilarSession }) {
  const badge = session.outcome ? outcomeBadge[session.outcome] : null

  return (
    <Link
      to={`/sessions/${session.session_id}`}
      className="block border-b border-border last:border-0 hover:bg-muted/50"
    >
      <div className="flex items-center gap-3 px-4 py-3">
        {session.engineer_avatar_url ? (
          <img
            src={session.engineer_avatar_url}
            alt={session.engineer_name}
            className="h-7 w-7 rounded-full"
          />
        ) : (
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-muted text-xs font-medium">
            {session.engineer_name.charAt(0)}
          </div>
        )}

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="truncate text-sm font-medium">{session.engineer_name}</span>
            {badge && (
              <Badge variant={badge.variant} className="text-[10px]">
                {badge.label}
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            {session.project_name && <span>{session.project_name}</span>}
            {session.session_type && (
              <>
                <span>-</span>
                <span>{session.session_type.replace(/_/g, " ")}</span>
              </>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span>{formatDuration(session.duration_seconds)}</span>
          {session.tools_used.length > 0 && (
            <div className="hidden gap-1 sm:flex">
              {session.tools_used.slice(0, 2).map((tool) => (
                <Badge key={tool} variant="secondary" className="text-[10px]">
                  {tool}
                </Badge>
              ))}
              {session.tools_used.length > 2 && (
                <span className="text-[10px] text-muted-foreground">
                  +{session.tools_used.length - 2}
                </span>
              )}
            </div>
          )}
        </div>

        <Badge variant="outline" className="hidden text-[10px] lg:inline-flex">
          {session.similarity_reason.replace(/_/g, " ")}
        </Badge>
      </div>
    </Link>
  )
}

export function SimilarSessionsPanel({ sessionId }: SimilarSessionsPanelProps) {
  const { data, isLoading } = useSimilarSessions(sessionId)

  if (isLoading) {
    return <CardSkeleton />
  }

  if (!data || data.similar_sessions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Similar Sessions</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-center text-sm text-muted-foreground">
            No similar sessions found.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">
          Similar Sessions ({data.total_found})
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        {data.similar_sessions.map((session) => (
          <SessionRow key={session.session_id} session={session} />
        ))}
      </CardContent>
    </Card>
  )
}
