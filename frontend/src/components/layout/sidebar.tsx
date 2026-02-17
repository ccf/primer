import { NavLink } from "react-router-dom"
import { LayoutDashboard, MonitorDot, Settings, Users, Users2, User } from "lucide-react"
import { cn } from "@/lib/utils"
import { useAuth } from "@/lib/auth-context"
import { getApiKey } from "@/lib/api"
import { getEffectiveRole } from "@/lib/role-utils"
import type { LucideIcon } from "lucide-react"

interface NavItem {
  to: string
  label: string
  icon: LucideIcon
}

const engineerLinks: NavItem[] = [
  { to: "/profile", label: "Home", icon: User },
  { to: "/sessions", label: "Sessions", icon: MonitorDot },
]

const leadershipLinks: NavItem[] = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/engineers", label: "Engineers", icon: Users },
  { to: "/teams", label: "Teams", icon: Users2 },
  { to: "/sessions", label: "Sessions", icon: MonitorDot },
]

const adminLink: NavItem = { to: "/admin", label: "Admin", icon: Settings }

export function Sidebar() {
  const { user } = useAuth()
  const isApiKeyUser = !user && !!getApiKey()
  const role = user?.role ?? (isApiKeyUser ? "admin" : "admin")
  const effectiveRole = getEffectiveRole(role)
  const isAdmin = role === "admin" || isApiKeyUser

  const links = effectiveRole === "leadership" ? leadershipLinks : engineerLinks
  const allLinks = isAdmin ? [...links, adminLink] : links

  return (
    <aside className="flex h-full w-48 flex-col border-r border-border bg-card">
      <div className="flex h-12 items-center gap-2 border-b border-border px-4">
        <img src="/logo-mark.svg" alt="Primer" className="h-5 w-5" />
        <span className="text-base font-semibold">Primer</span>
      </div>
      <nav className="flex-1 space-y-1 p-3">
        {allLinks.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
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
