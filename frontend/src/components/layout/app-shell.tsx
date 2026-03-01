import { useState, useCallback, useEffect, type ReactNode } from "react"
import { useLocation } from "react-router-dom"
import { Sidebar } from "./sidebar"
import { Header } from "./header"
import type { DateRange } from "./date-range-picker"
import { SIDEBAR_KEY } from "@/lib/constants"

interface AppShellProps {
  children: ReactNode
  teamId: string | null
  onTeamChange: (id: string | null) => void
  dateRange: DateRange | null
  onDateRangeChange: (range: DateRange | null) => void
}

export function AppShell({ children, teamId, onTeamChange, dateRange, onDateRangeChange }: AppShellProps) {
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem(SIDEBAR_KEY) === "true" } catch { return false }
  })

  // Sync sidebar state from other tabs via storage events
  useEffect(() => {
    const sync = () => {
      try {
        setCollapsed(localStorage.getItem(SIDEBAR_KEY) === "true")
      } catch { /* noop */ }
    }
    window.addEventListener("storage", sync)
    return () => window.removeEventListener("storage", sync)
  }, [])

  const toggleSidebar = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev
      try { localStorage.setItem(SIDEBAR_KEY, String(next)) } catch { /* noop */ }
      window.dispatchEvent(new Event("sidebar-toggle"))
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
        <main className="flex flex-1 flex-col overflow-y-auto p-6">
          <div key={location.pathname} className="mx-auto w-full max-w-[1280px] flex-1 animate-fade-in">{children}</div>
        </main>
      </div>
    </div>
  )
}
