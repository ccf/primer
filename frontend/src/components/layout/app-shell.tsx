import type { ReactNode } from "react"
import { Sidebar } from "./sidebar"
import { Header } from "./header"

interface AppShellProps {
  children: ReactNode
  teamId: string | null
  onTeamChange: (id: string | null) => void
}

export function AppShell({ children, teamId, onTeamChange }: AppShellProps) {
  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header teamId={teamId} onTeamChange={onTeamChange} />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  )
}
