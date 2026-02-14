import { useState, useEffect, useCallback } from "react"
import { Search, X } from "lucide-react"
import { Button } from "@/components/ui/button"

interface FilterState {
  outcome: string
  sessionType: string
  primaryModel: string
  gitBranch: string
}

interface SessionSearchBarProps {
  search: string
  onSearchChange: (value: string) => void
  filters: FilterState
  onFilterChange: (filters: FilterState) => void
}

const OUTCOMES = ["success", "partial", "failure", "abandoned"]
const SESSION_TYPES = ["feature", "debugging", "refactoring", "exploration", "documentation"]

export function SessionSearchBar({
  search,
  onSearchChange,
  filters,
  onFilterChange,
}: SessionSearchBarProps) {
  const [localSearch, setLocalSearch] = useState(search)

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      onSearchChange(localSearch)
    }, 300)
    return () => clearTimeout(timer)
  }, [localSearch, onSearchChange])

  // Sync external search changes
  useEffect(() => {
    setLocalSearch(search)
  }, [search])

  const updateFilter = useCallback(
    (key: keyof FilterState, value: string) => {
      onFilterChange({ ...filters, [key]: value })
    },
    [filters, onFilterChange],
  )

  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="relative flex-1 min-w-[200px]">
        <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search sessions..."
          value={localSearch}
          onChange={(e) => setLocalSearch(e.target.value)}
          className="h-8 w-full rounded-md border border-input bg-background pl-8 pr-8 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
        />
        {localSearch && (
          <button
            onClick={() => {
              setLocalSearch("")
              onSearchChange("")
            }}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
      <select
        value={filters.outcome}
        onChange={(e) => updateFilter("outcome", e.target.value)}
        className="h-8 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
      >
        <option value="">All outcomes</option>
        {OUTCOMES.map((o) => (
          <option key={o} value={o}>
            {o.charAt(0).toUpperCase() + o.slice(1)}
          </option>
        ))}
      </select>
      <select
        value={filters.sessionType}
        onChange={(e) => updateFilter("sessionType", e.target.value)}
        className="h-8 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
      >
        <option value="">All types</option>
        {SESSION_TYPES.map((t) => (
          <option key={t} value={t}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </option>
        ))}
      </select>
    </div>
  )
}

export function ActiveFilterChips({
  filters,
  search,
  onClear,
}: {
  filters: FilterState
  search: string
  onClear: (key: string) => void
}) {
  const chips = [
    ...(search ? [{ key: "search", label: `Search: "${search}"` }] : []),
    ...(filters.outcome ? [{ key: "outcome", label: `Outcome: ${filters.outcome}` }] : []),
    ...(filters.sessionType
      ? [{ key: "sessionType", label: `Type: ${filters.sessionType}` }]
      : []),
    ...(filters.primaryModel
      ? [{ key: "primaryModel", label: `Model: ${filters.primaryModel}` }]
      : []),
    ...(filters.gitBranch ? [{ key: "gitBranch", label: `Branch: ${filters.gitBranch}` }] : []),
  ]

  if (chips.length === 0) return null

  return (
    <div className="flex flex-wrap gap-2">
      {chips.map((c) => (
        <Button key={c.key} variant="secondary" size="sm" onClick={() => onClear(c.key)}>
          {c.label}
          <X className="ml-1 h-3 w-3" />
        </Button>
      ))}
    </div>
  )
}
