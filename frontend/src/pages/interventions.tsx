import { useMemo, useState } from "react"
import { ClipboardList, PlayCircle, CheckCircle2, Target, Plus } from "lucide-react"
import { PageHeader } from "@/components/shared/page-header"
import { CardSkeleton } from "@/components/shared/loading-skeleton"
import { EmptyState } from "@/components/shared/empty-state"
import { InterventionCard } from "@/components/interventions/intervention-card"
import { InterventionFormModal } from "@/components/interventions/intervention-form-modal"
import { InlineStat } from "@/components/ui/inline-stat"
import { Button } from "@/components/ui/button"
import { useEngineers, useInterventions } from "@/hooks/use-api-queries"
import { useAuth } from "@/lib/auth-context"
import { getEffectiveRole } from "@/lib/role-utils"

interface InterventionsPageProps {
  teamId: string | null
}

export function InterventionsPage({ teamId }: InterventionsPageProps) {
  const { user } = useAuth()
  const effectiveRole = getEffectiveRole(user?.role ?? "engineer")
  const isLeadership = effectiveRole === "leadership"
  const [showCreateModal, setShowCreateModal] = useState(false)

  const { data: interventions, isLoading } = useInterventions({
    teamId,
    engineerId: !isLeadership ? user?.engineer_id : undefined,
  })
  const { data: engineers } = useEngineers()

  const ownerOptions = useMemo(
    () => (engineers ?? []).filter((engineer) => (teamId ? engineer.team_id === teamId : true)),
    [engineers, teamId],
  )

  if (isLoading) {
    return (
      <div className="space-y-6">
        <CardSkeleton />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <CardSkeleton key={index} />
          ))}
        </div>
        <CardSkeleton />
      </div>
    )
  }

  if (!interventions) return null

  const plannedCount = interventions.filter((item) => item.status === "planned").length
  const inProgressCount = interventions.filter((item) => item.status === "in_progress").length
  const completedCount = interventions.filter((item) => item.status === "completed").length
  const assignedCount = interventions.filter((item) => item.owner_engineer_id).length

  return (
    <div className="space-y-8">
      <PageHeader
        icon={ClipboardList}
        title="Interventions"
        description="Tracked follow-through for recommendations, coaching, and workflow changes"
      >
        <Button onClick={() => setShowCreateModal(true)}>
          <Plus className="mr-1 h-4 w-4" />
          New intervention
        </Button>
      </PageHeader>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <InlineStat label="Planned" value={String(plannedCount)} icon={Target} />
        <InlineStat label="In Progress" value={String(inProgressCount)} icon={PlayCircle} />
        <InlineStat label="Completed" value={String(completedCount)} icon={CheckCircle2} />
        <InlineStat label="Assigned" value={String(assignedCount)} icon={ClipboardList} />
      </div>

      {interventions.length === 0 ? (
        <EmptyState message="No interventions yet. Create one from a recommendation or start a manual experiment." />
      ) : (
        <div className="space-y-4">
          {interventions.map((intervention) => (
            <InterventionCard
              key={intervention.id}
              intervention={intervention}
              ownerOptions={ownerOptions}
              canManage={true}
              canManageOwner={isLeadership}
            />
          ))}
        </div>
      )}

      <InterventionFormModal
        open={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        teamId={teamId}
        defaultOwnerEngineerId={user?.engineer_id ?? null}
      />
    </div>
  )
}
