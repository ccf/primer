import { useState, useCallback } from "react"
import { useSearchParams } from "react-router-dom"
import { useAuth } from "@/lib/auth-context"
import { useSessions, useEngineers, useFriction } from "@/hooks/use-api-queries"
import { SessionTable } from "@/components/sessions/session-table"
import { SessionFilters } from "@/components/sessions/session-filters"
import { SessionSearchBar, ActiveFilterChips } from "@/components/sessions/session-search-bar"
import { FrictionList } from "@/components/analytics/friction-list"
import { TableSkeleton, ChartSkeleton } from "@/components/shared/loading-skeleton"
import { EmptyState } from "@/components/shared/empty-state"
import { Button } from "@/components/ui/button"
import { ChevronLeft, ChevronRight, Download, X } from "lucide-react"
import { useKeyboardNavigation } from "@/hooks/use-keyboard-navigation"
import { exportToCsv } from "@/lib/csv-export"
import type { DateRange } from "@/components/layout/date-range-picker"

interface SessionsPageProps {
  teamId: string | null
  dateRange: DateRange | null
}

const PAGE_SIZE = 50

export function SessionsPage({ teamId, dateRange }: SessionsPageProps) {
  const { user } = useAuth()
  const role = user?.role ?? "admin"
  const [searchParams, setSearchParams] = useSearchParams()
  const [engineerId, setEngineerId] = useState(searchParams.get("engineer_id") ?? "")
  const [offset, setOffset] = useState(0)
  const [search, setSearch] = useState("")
  const [advFilters, setAdvFilters] = useState({
    outcome: "",
    sessionType: "",
    primaryModel: "",
    gitBranch: "",
  })

  const projectFilter = searchParams.get("project") ?? undefined
  const frictionFilter = searchParams.get("friction_type") ?? undefined

  const startDate = dateRange?.startDate
  const endDate = dateRange?.endDate

  const { data: engineers } = useEngineers()
  const { data: sessions, isLoading: loadingSessions } = useSessions({
    teamId,
    engineerId: engineerId || undefined,
    projectName: projectFilter,
    search: search || undefined,
    outcome: advFilters.outcome || undefined,
    sessionType: advFilters.sessionType || undefined,
    primaryModel: advFilters.primaryModel || undefined,
    gitBranch: advFilters.gitBranch || undefined,
    startDate,
    endDate,
    limit: PAGE_SIZE,
    offset,
  })
  const { data: friction, isLoading: loadingFriction } = useFriction(teamId, startDate, endDate)

  const { selectedIndex } = useKeyboardNavigation({
    items: sessions ?? [],
    enabled: !loadingSessions && !!sessions && sessions.length > 0,
  })

  const handleSearchChange = useCallback((value: string) => {
    setSearch(value)
    setOffset(0)
  }, [])

  const handleAdvFilterChange = useCallback((filters: typeof advFilters) => {
    setAdvFilters(filters)
    setOffset(0)
  }, [])

  const clearFilter = (key: string) => {
    if (key === "search") {
      setSearch("")
    } else if (key === "engineer_id") {
      setEngineerId("")
    } else if (key in advFilters) {
      setAdvFilters((prev) => ({ ...prev, [key]: "" }))
    } else {
      searchParams.delete(key)
      setSearchParams(searchParams)
    }
    setOffset(0)
  }

  const handleExport = () => {
    if (!sessions) return
    exportToCsv(
      "sessions.csv",
      ["ID", "Engineer", "Project", "Started", "Duration (s)", "Messages", "Tool Calls", "Model", "Tokens In", "Tokens Out"],
      sessions.map((s) => [
        s.id,
        s.engineer_id,
        s.project_name ?? "",
        s.started_at ?? "",
        s.duration_seconds ?? "",
        s.message_count,
        s.tool_call_count,
        s.primary_model ?? "",
        s.input_tokens,
        s.output_tokens,
      ]),
    )
  }

  const legacyFilters = [
    ...(projectFilter ? [{ key: "project", label: `Project: ${projectFilter}` }] : []),
    ...(frictionFilter ? [{ key: "friction_type", label: `Friction: ${frictionFilter}` }] : []),
    ...(engineerId ? [{ key: "engineer_id", label: "Engineer filtered" }] : []),
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">
          {role === "engineer" ? "My Sessions" : "Sessions"}
        </h1>
        <div className="flex items-center gap-2">
          {sessions && sessions.length > 0 && (
            <Button variant="outline" size="sm" onClick={handleExport}>
              <Download className="mr-1 h-4 w-4" />
              Export CSV
            </Button>
          )}
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
      </div>

      {/* Search and advanced filters */}
      <SessionSearchBar
        search={search}
        onSearchChange={handleSearchChange}
        filters={advFilters}
        onFilterChange={handleAdvFilterChange}
      />

      {/* Active filter chips */}
      <ActiveFilterChips filters={advFilters} search={search} onClear={clearFilter} />
      {legacyFilters.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {legacyFilters.map((f) => (
            <Button
              key={f.key}
              variant="secondary"
              size="sm"
              onClick={() => clearFilter(f.key)}
            >
              {f.label}
              <X className="ml-1 h-3 w-3" />
            </Button>
          ))}
        </div>
      )}

      {loadingSessions ? (
        <TableSkeleton />
      ) : !sessions || sessions.length === 0 ? (
        <EmptyState message="No sessions found" />
      ) : (
        <>
          <SessionTable sessions={sessions} selectedIndex={selectedIndex} />
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
