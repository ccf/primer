import { useState } from "react"
import { useParams, Link } from "react-router-dom"
import { useSessionDetail } from "@/hooks/use-api-queries"
import { SessionDetailPanel } from "@/components/sessions/session-detail-panel"
import { CardSkeleton } from "@/components/shared/loading-skeleton"
import { ArrowLeft, Link2, Check } from "lucide-react"

export function SessionDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: session, isLoading } = useSessionDetail(id ?? "")
  const [copied, setCopied] = useState(false)

  const handleCopyLink = async () => {
    await navigator.clipboard.writeText(window.location.href)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

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
      <div className="flex items-center gap-3">
        <Link
          to="/sessions"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to sessions
        </Link>
        <button
          onClick={handleCopyLink}
          className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5" />
              Copied!
            </>
          ) : (
            <>
              <Link2 className="h-3.5 w-3.5" />
              Copy link
            </>
          )}
        </button>
      </div>
      <SessionDetailPanel session={session} />
    </div>
  )
}
