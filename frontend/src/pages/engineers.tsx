import { useEngineers, useTeams } from "@/hooks/use-api-queries"
import { EngineerTable } from "@/components/engineers/engineer-table"
import { TableSkeleton } from "@/components/shared/loading-skeleton"
import { EmptyState } from "@/components/shared/empty-state"

export function EngineersPage() {
  const { data: engineers, isLoading: loadingEngineers } = useEngineers()
  const { data: teams, isLoading: loadingTeams } = useTeams()

  if (loadingEngineers || loadingTeams) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Engineers</h1>
        <TableSkeleton />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Engineers</h1>
      {!engineers || engineers.length === 0 ? (
        <EmptyState message="No engineers found" />
      ) : (
        <EngineerTable engineers={engineers} teams={teams ?? []} />
      )}
    </div>
  )
}
