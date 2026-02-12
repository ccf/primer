import { useParams, Link } from "react-router-dom"
import { useSessionDetail } from "@/hooks/use-api-queries"
import { SessionDetailPanel } from "@/components/sessions/session-detail-panel"
import { CardSkeleton } from "@/components/shared/loading-skeleton"
import { ArrowLeft } from "lucide-react"

export function SessionDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: session, isLoading } = useSessionDetail(id ?? "")

  if (isLoading) {
    return (
      <div className="space-y-4">
        <CardSkeleton />
        <CardSkeleton />
      </div>
    )
  }

  if (!session) {
    return (
      <div className="text-center">
        <p className="text-muted-foreground">Session not found</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <Link
        to="/sessions"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to sessions
      </Link>
      <SessionDetailPanel session={session} />
    </div>
  )
}
