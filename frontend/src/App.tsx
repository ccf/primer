import { useState } from "react"
import { BrowserRouter, Route, Routes } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { getApiKey } from "@/lib/api"
import { LoginGate } from "@/components/shared/login-gate"
import { AppShell } from "@/components/layout/app-shell"
import { OverviewPage } from "@/pages/overview"
import { SessionsPage } from "@/pages/sessions"
import { SessionDetailPage } from "@/pages/session-detail"
import { EngineersPage } from "@/pages/engineers"
import { NotFoundPage } from "@/pages/not-found"

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
})

export default function App() {
  const [teamId, setTeamId] = useState<string | null>(null)

  if (!getApiKey()) {
    return (
      <QueryClientProvider client={queryClient}>
        <LoginGate />
      </QueryClientProvider>
    )
  }

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppShell teamId={teamId} onTeamChange={setTeamId}>
          <Routes>
            <Route path="/" element={<OverviewPage teamId={teamId} />} />
            <Route path="/sessions" element={<SessionsPage teamId={teamId} />} />
            <Route path="/sessions/:id" element={<SessionDetailPage />} />
            <Route path="/engineers" element={<EngineersPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </AppShell>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
