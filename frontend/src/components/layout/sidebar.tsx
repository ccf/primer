import { NavLink } from "react-router-dom"
import { LayoutDashboard, MonitorDot, Settings, Sparkles, Users, Users2, User } from "lucide-react"
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
  { to: "/synthesis", label: "Synthesis", icon: Sparkles },
]

const leadershipLinks: NavItem[] = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/engineers", label: "Engineers", icon: Users },
  { to: "/teams", label: "Teams", icon: Users2 },
  { to: "/sessions", label: "Sessions", icon: MonitorDot },
  { to: "/maturity", label: "AI Maturity", icon: Sparkles },
  { to: "/synthesis", label: "Synthesis", icon: Sparkles },
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
    </aside>
  )
}
