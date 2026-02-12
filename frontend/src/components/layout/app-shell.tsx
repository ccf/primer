import type { ReactNode } from "react"
import { Sidebar } from "./sidebar"
import { Header } from "./header"
import type { DateRange } from "./date-range-picker"

interface AppShellProps {
  children: ReactNode
  teamId: string | null
  onTeamChange: (id: string | null) => void
  dateRange: DateRange | null
  onDateRangeChange: (range: DateRange | null) => void
}

export function AppShell({ children, teamId, onTeamChange, dateRange, onDateRangeChange }: AppShellProps) {
  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header
          teamId={teamId}
          onTeamChange={onTeamChange}
          dateRange={dateRange}
          onDateRangeChange={onDateRangeChange}
        />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  )
}
