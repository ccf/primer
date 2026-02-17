import { useState } from "react"
import { BrowserRouter, Route, Routes, useParams } from "react-router-dom"
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
import { ProjectsPage } from "@/pages/projects"
import { TeamsPage } from "@/pages/teams"
import { TeamDetailPage } from "@/pages/team-detail"
import { BottlenecksPage } from "@/pages/bottlenecks"
import { ToolAdoptionPage } from "@/pages/tool-adoption"
import { InsightsPage } from "@/pages/insights"
import { GrowthPage } from "@/pages/growth"
import { QualityPage } from "@/pages/quality"
import { SessionInsightsPage } from "@/pages/session-insights"
import { MaturityPage } from "@/pages/maturity"
import { AdminPage } from "@/pages/admin"
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
        <Route path="/engineers/:id" element={<EngineerProfileRoute dateRange={dateRange} />} />
        <Route path="/engineers" element={<EngineersPage teamId={teamId} dateRange={dateRange} />} />
        <Route path="/projects" element={<ProjectsPage teamId={teamId} dateRange={dateRange} />} />
        <Route path="/bottlenecks" element={<BottlenecksPage teamId={teamId} dateRange={dateRange} />} />
        <Route path="/tool-adoption" element={<ToolAdoptionPage teamId={teamId} dateRange={dateRange} />} />
        <Route path="/insights" element={<InsightsPage teamId={teamId} dateRange={dateRange} />} />
        <Route path="/growth" element={<GrowthPage teamId={teamId} dateRange={dateRange} />} />
        <Route path="/quality" element={<QualityPage teamId={teamId} dateRange={dateRange} />} />
        <Route path="/session-insights" element={<SessionInsightsPage teamId={teamId} dateRange={dateRange} />} />
        <Route path="/maturity" element={<MaturityPage teamId={teamId} dateRange={dateRange} />} />
        <Route path="/teams" element={<TeamsPage />} />
        <Route path="/teams/:teamId" element={<TeamDetailRoute dateRange={dateRange} />} />
        <Route path="/admin" element={<AdminPage />} />
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
