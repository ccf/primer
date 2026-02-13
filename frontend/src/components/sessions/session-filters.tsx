import type { EngineerResponse } from "@/types/api"

interface SessionFiltersProps {
  engineers: EngineerResponse[]
  engineerId: string
  onEngineerChange: (id: string) => void
}

export function SessionFilters({ engineers, engineerId, onEngineerChange }: SessionFiltersProps) {
  return (
    <div className="flex items-center gap-3">
      <select
        value={engineerId}
        onChange={(e) => onEngineerChange(e.target.value)}
        className="h-8 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
      >
        <option value="">All engineers</option>
        {engineers.map((eng) => (
          <option key={eng.id} value={eng.id}>
            {eng.name}
          </option>
        ))}
      </select>
    </div>
  )
}
