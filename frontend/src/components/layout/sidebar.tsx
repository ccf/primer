import { NavLink } from "react-router-dom"
import { AlertTriangle, FolderKanban, GitPullRequest, GraduationCap, Layout, Lightbulb, Microscope, MonitorDot, Settings, Sparkles, Users, Users2, Wrench } from "lucide-react"
import { cn } from "@/lib/utils"
import { useAuth } from "@/lib/auth-context"
import { getApiKey } from "@/lib/api"

const allLinks = [
  { to: "/", label: "Overview", icon: Layout, minRole: "engineer" as const },
  { to: "/sessions", label: "Sessions", icon: MonitorDot, minRole: "engineer" as const },
  { to: "/projects", label: "Projects", icon: FolderKanban, minRole: "engineer" as const },
  { to: "/bottlenecks", label: "Bottlenecks", icon: AlertTriangle, minRole: "engineer" as const },
  { to: "/tool-adoption", label: "Tool Adoption", icon: Wrench, minRole: "engineer" as const },
  { to: "/insights", label: "Insights", icon: Lightbulb, minRole: "engineer" as const },
  { to: "/growth", label: "Growth", icon: GraduationCap, minRole: "engineer" as const },
  { to: "/quality", label: "Quality", icon: GitPullRequest, minRole: "engineer" as const },
  { to: "/session-insights", label: "Session Insights", icon: Microscope, minRole: "engineer" as const },
  { to: "/maturity", label: "AI Maturity", icon: Sparkles, minRole: "engineer" as const },
  { to: "/teams", label: "Teams", icon: Users2, minRole: "team_lead" as const },
  { to: "/engineers", label: "Engineers", icon: Users, minRole: "team_lead" as const },
  { to: "/admin", label: "Admin", icon: Settings, minRole: "admin" as const },
]

const roleLevel: Record<string, number> = {
  engineer: 0,
  team_lead: 1,
  admin: 2,
}

export function Sidebar() {
  const { user } = useAuth()
  const isApiKeyUser = !user && !!getApiKey()
  const role = user?.role ?? (isApiKeyUser ? "admin" : "admin")
  const level = roleLevel[role] ?? 0

  const visibleLinks = allLinks.filter((link) => level >= (roleLevel[link.minRole] ?? 0))

  return (
    <aside className="flex h-full w-56 flex-col border-r border-border bg-card">
      <div className="flex h-14 items-center gap-2 border-b border-border px-4">
        <img src="/logo-mark.svg" alt="Primer" className="h-6 w-6" />
        <span className="text-lg font-semibold">Primer</span>
      </div>
      <nav className="flex-1 space-y-1 p-3">
        {visibleLinks.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.to === "/"}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
              )
            }
          >
            <link.icon className="h-4 w-4" />
            {link.label}
          </NavLink>
        ))}
      </nav>

      {/* User profile section */}
      {user && (
        <div className="border-t border-border p-3">
          <div className="flex items-center gap-2">
            {user.avatar_url ? (
              <img
                src={user.avatar_url}
                alt={user.display_name ?? user.name}
                className="h-8 w-8 rounded-full"
              />
            ) : (
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-xs font-medium">
                {(user.display_name ?? user.name).charAt(0).toUpperCase()}
              </div>
            )}
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">
                {user.display_name ?? user.name}
              </p>
              {user.github_username && (
                <p className="truncate text-xs text-muted-foreground">
                  @{user.github_username}
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </aside>
  )
}
