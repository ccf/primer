import { useState } from "react"
import { BrowserRouter, Route, Routes } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { getApiKey } from "@/lib/api"
import { AuthProvider, useAuth } from "@/lib/auth-context"
import { ThemeProvider } from "@/lib/theme-context"
import { LoginPage } from "@/pages/login"
import { AuthCallbackPage } from "@/pages/auth-callback"
import { AppShell } from "@/components/layout/app-shell"
import { OverviewPage } from "@/pages/overview"
import { SessionsPage } from "@/pages/sessions"
import { SessionDetailPage } from "@/pages/session-detail"
import { EngineersPage } from "@/pages/engineers"
import { NotFoundPage } from "@/pages/not-found"
import type { DateRange } from "@/components/layout/date-range-picker"

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
})

function AuthenticatedApp() {
  const { user, loading } = useAuth()
  const [teamId, setTeamId] = useState<string | null>(null)
  const [dateRange, setDateRange] = useState<DateRange | null>(null)

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    )
  }

  // Check both OAuth user and legacy API key
  if (!user && !getApiKey()) {
    return <LoginPage />
  }

  return (
    <AppShell
      teamId={teamId}
      onTeamChange={setTeamId}
      dateRange={dateRange}
      onDateRangeChange={setDateRange}
    >
      <Routes>
        <Route path="/" element={<OverviewPage teamId={teamId} dateRange={dateRange} />} />
        <Route path="/sessions" element={<SessionsPage teamId={teamId} dateRange={dateRange} />} />
        <Route path="/sessions/:id" element={<SessionDetailPage />} />
        <Route path="/engineers" element={<EngineersPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AppShell>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ThemeProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/auth/callback" element={<AuthCallbackPage />} />
              <Route path="/*" element={<AuthenticatedApp />} />
            </Routes>
          </BrowserRouter>
        </ThemeProvider>
      </AuthProvider>
    </QueryClientProvider>
  )
}
