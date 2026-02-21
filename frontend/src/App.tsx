import { useState } from "react"
import { BrowserRouter, Navigate, Route, Routes, useParams } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { getApiKey } from "@/lib/api"
import { AuthProvider, useAuth } from "@/lib/auth-context"
import { ThemeProvider } from "@/lib/theme-context"
import { getDefaultRoute } from "@/lib/role-utils"
import { LoginPage } from "@/pages/login"
import { AuthCallbackPage } from "@/pages/auth-callback"
import { AppShell } from "@/components/layout/app-shell"
import { ProfilePage } from "@/pages/profile"
import { DashboardPage } from "@/pages/dashboard"
import { SessionsPage } from "@/pages/sessions"
import { SessionDetailPage } from "@/pages/session-detail"
import { EngineersPage } from "@/pages/engineers"
import { TeamsPage } from "@/pages/teams"
import { TeamDetailPage } from "@/pages/team-detail"
import { MaturityPage } from "@/pages/maturity"
import { NarrativePage } from "@/pages/narrative"
import { AdminPage } from "@/pages/admin"
import { ExplorerPage } from "@/pages/explorer"
import { EngineerProfilePage } from "@/pages/engineer-profile"
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

function TeamDetailRoute({ dateRange }: { dateRange: DateRange | null }) {
  const { teamId } = useParams<{ teamId: string }>()
  return <TeamDetailPage teamId={teamId ?? ""} dateRange={dateRange} />
}

function EngineerProfileRoute({ dateRange }: { dateRange: DateRange | null }) {
  return <EngineerProfilePage dateRange={dateRange} />
}

function RoleRedirect() {
  const { user } = useAuth()
  const isApiKeyUser = !user && !!getApiKey()
  const role = user?.role ?? (isApiKeyUser ? "admin" : "engineer")
  return <Navigate to={getDefaultRoute(role)} replace />
}

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
        <Route path="/" element={<RoleRedirect />} />
        <Route path="/profile" element={<ProfilePage teamId={teamId} dateRange={dateRange} />} />
        <Route path="/dashboard" element={<DashboardPage teamId={teamId} dateRange={dateRange} />} />
        <Route path="/sessions" element={<SessionsPage teamId={teamId} dateRange={dateRange} />} />
        <Route path="/sessions/:id" element={<SessionDetailPage />} />
        <Route path="/engineers/:id" element={<EngineerProfileRoute dateRange={dateRange} />} />
        <Route path="/engineers" element={<EngineersPage teamId={teamId} dateRange={dateRange} />} />
        <Route path="/maturity" element={<MaturityPage teamId={teamId} dateRange={dateRange} />} />
        <Route path="/teams" element={<TeamsPage />} />
        <Route path="/teams/:teamId" element={<TeamDetailRoute dateRange={dateRange} />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/explorer" element={<ExplorerPage teamId={teamId} dateRange={dateRange} />} />

        <Route path="/synthesis" element={<NarrativePage teamId={teamId} dateRange={dateRange} />} />

        {/* Redirects for deprecated routes */}
        <Route path="/overview" element={<Navigate to="/" replace />} />
        <Route path="/bottlenecks" element={<Navigate to="/" replace />} />
        <Route path="/tool-adoption" element={<Navigate to="/" replace />} />
        <Route path="/insights" element={<Navigate to="/synthesis" replace />} />
        <Route path="/growth" element={<Navigate to="/" replace />} />
        <Route path="/quality" element={<Navigate to="/" replace />} />
        <Route path="/session-insights" element={<Navigate to="/" replace />} />
        <Route path="/projects" element={<Navigate to="/" replace />} />

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
