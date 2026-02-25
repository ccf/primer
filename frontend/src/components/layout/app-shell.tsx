import { useState, useCallback, type ReactNode } from "react"
import { Sidebar } from "./sidebar"
import { Header } from "./header"
import type { DateRange } from "./date-range-picker"

const SIDEBAR_KEY = "primer-sidebar-collapsed"

interface AppShellProps {
  children: ReactNode
  teamId: string | null
  onTeamChange: (id: string | null) => void
  dateRange: DateRange | null
  onDateRangeChange: (range: DateRange | null) => void
}

export function AppShell({ children, teamId, onTeamChange, dateRange, onDateRangeChange }: AppShellProps) {
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(SIDEBAR_KEY) === "true")

  const toggleSidebar = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev
      localStorage.setItem(SIDEBAR_KEY, String(next))
      return next
    })
  }, [])

  return (
    <div className="flex h-screen">
      <Sidebar collapsed={collapsed} onToggle={toggleSidebar} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header
          teamId={teamId}
          onTeamChange={onTeamChange}
          dateRange={dateRange}
          onDateRangeChange={onDateRangeChange}
          sidebarCollapsed={collapsed}
          onToggleSidebar={toggleSidebar}
        />
        <main className="flex-1 overflow-y-auto p-6">
          <div className="mx-auto max-w-[1280px]">{children}</div>
        </main>
      </div>
    </div>
  )
}
