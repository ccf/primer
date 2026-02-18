import { useState } from "react"
import { AlertCircle, Lightbulb, ServerOff } from "lucide-react"
import { cn } from "@/lib/utils"
import { useAuth } from "@/lib/auth-context"
import { getApiKey } from "@/lib/api"
import { getEffectiveRole } from "@/lib/role-utils"
import { useNarrative, useNarrativeStatus } from "@/hooks/use-api-queries"
import { useRefreshNarrative } from "@/hooks/use-api-mutations"
import { NarrativeReport } from "@/components/narrative/narrative-report"
import { NarrativeSkeleton } from "@/components/narrative/narrative-skeleton"
import type { DateRange } from "@/components/layout/date-range-picker"

type Scope = "engineer" | "team" | "org"

interface NarrativePageProps {
  teamId: string | null
  dateRange: DateRange | null
}

export function NarrativePage({ teamId, dateRange }: NarrativePageProps) {
  const { user } = useAuth()
  const isApiKeyUser = !user && !!getApiKey()
  const role = user?.role ?? (isApiKeyUser ? "admin" : "engineer")
  const effectiveRole = getEffectiveRole(role)
  const isLeadership = effectiveRole === "leadership"

  const [scope, setScope] = useState<Scope>(isLeadership ? "team" : "engineer")

  const startDate = dateRange?.startDate
  const endDate = dateRange?.endDate

  const { data: status, isLoading: statusLoading } = useNarrativeStatus()
  const { data, isLoading, error } = useNarrative(
    scope,
    scope === "team" ? teamId : undefined,
    startDate,
    endDate,
    status?.available !== false,
  )

  const refreshMutation = useRefreshNarrative()

  const handleRefresh = () => {
    refreshMutation.mutate({
      scope,
      teamId: scope === "team" ? teamId : undefined,
      startDate,
      endDate,
    })
  }

  const scopeButtons: { value: Scope; label: string; visible: boolean }[] = [
    { value: "engineer", label: "My Report", visible: !!user },
    { value: "team", label: "Team", visible: isLeadership || !!user?.team_id },
    { value: "org", label: "Organization", visible: role === "admin" || role === "team_lead" || isApiKeyUser },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Lightbulb className="h-6 w-6 text-primary" />
        <h1 className="text-2xl font-bold">Insights</h1>
      </div>

      {/* Scope selector */}
      <div className="flex gap-1">
        {scopeButtons
          .filter((b) => b.visible)
          .map((btn) => (
            <button
              key={btn.value}
              onClick={() => setScope(btn.value)}
              className={cn(
                "rounded-lg px-4 py-2 text-sm font-medium transition-colors",
                scope === btn.value
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-accent hover:text-accent-foreground",
              )}
            >
              {btn.label}
            </button>
          ))}
      </div>

      {/* Content */}
      {statusLoading ? (
        <div className="py-12 text-center text-sm text-muted-foreground">
          Checking availability...
        </div>
      ) : status?.available === false ? (
        <div className="flex flex-col items-center gap-3 py-16 text-center">
          <ServerOff className="h-10 w-10 text-muted-foreground" />
          <h3 className="text-lg font-semibold">Insights not available</h3>
          <p className="max-w-md text-sm text-muted-foreground">
            Set the <code className="rounded bg-muted px-1.5 py-0.5 text-xs">PRIMER_ANTHROPIC_API_KEY</code> environment
            variable to enable LLM-generated narrative insights.
          </p>
        </div>
      ) : isLoading || refreshMutation.isPending ? (
        <NarrativeSkeleton />
      ) : error ? (
        <div className="flex flex-col items-center gap-3 py-16 text-center">
          <AlertCircle className="h-10 w-10 text-destructive" />
          <h3 className="text-lg font-semibold">Failed to generate insights</h3>
          <p className="max-w-md text-sm text-muted-foreground">
            {error instanceof Error ? error.message : "An unexpected error occurred"}
          </p>
        </div>
      ) : data ? (
        <NarrativeReport
          data={refreshMutation.data ?? data}
          onRefresh={handleRefresh}
          isRefreshing={refreshMutation.isPending}
        />
      ) : null}
    </div>
  )
}
