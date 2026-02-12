import { useState } from "react"
import { useAuth } from "@/lib/auth-context"
import { useSessions, useEngineers, useFriction } from "@/hooks/use-api-queries"
import { SessionTable } from "@/components/sessions/session-table"
import { SessionFilters } from "@/components/sessions/session-filters"
import { FrictionList } from "@/components/analytics/friction-list"
import { TableSkeleton, ChartSkeleton } from "@/components/shared/loading-skeleton"
import { EmptyState } from "@/components/shared/empty-state"
import { Button } from "@/components/ui/button"
import { ChevronLeft, ChevronRight } from "lucide-react"

interface SessionsPageProps {
  teamId: string | null
}

const PAGE_SIZE = 50

export function SessionsPage({ teamId }: SessionsPageProps) {
  const { user } = useAuth()
  const role = user?.role ?? "admin"
  const [engineerId, setEngineerId] = useState("")
  const [offset, setOffset] = useState(0)

  const { data: engineers } = useEngineers()
  const { data: sessions, isLoading: loadingSessions } = useSessions({
    teamId,
    engineerId: engineerId || undefined,
    limit: PAGE_SIZE,
    offset,
  })
  const { data: friction, isLoading: loadingFriction } = useFriction(teamId)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">
          {role === "engineer" ? "My Sessions" : "Sessions"}
        </h1>
        {role === "admin" && (
          <SessionFilters
            engineers={engineers ?? []}
            engineerId={engineerId}
            onEngineerChange={(id) => {
              setEngineerId(id)
              setOffset(0)
            }}
          />
        )}
      </div>

      {loadingSessions ? (
        <TableSkeleton />
      ) : !sessions || sessions.length === 0 ? (
        <EmptyState message="No sessions found" />
      ) : (
        <>
          <SessionTable sessions={sessions} />
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Showing {offset + 1}–{offset + sessions.length}
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              >
                <ChevronLeft className="mr-1 h-4 w-4" />
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={sessions.length < PAGE_SIZE}
                onClick={() => setOffset(offset + PAGE_SIZE)}
              >
                Next
                <ChevronRight className="ml-1 h-4 w-4" />
              </Button>
            </div>
          </div>
        </>
      )}

      {/* Friction Report */}
      {loadingFriction ? <ChartSkeleton /> : friction && <FrictionList data={friction} />}
    </div>
  )
}
