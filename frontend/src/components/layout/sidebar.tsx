import { useState, useRef, useEffect } from "react"
import { NavLink, useNavigate } from "react-router-dom"
import {
  AlertTriangle,
  DollarSign,
  FolderKanban,
  GitPullRequest,
  GraduationCap,
  LayoutDashboard,
  MessageSquare,
  MonitorDot,
  Settings,
  Sparkles,
  TrendingUp,
  Users,
  Users2,
  User,
  LogOut,
  Sun,
  Moon,
  PanelLeft,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useAuth } from "@/lib/auth-context"
import { useTheme } from "@/lib/theme-context"
import { getApiKey, clearApiKey } from "@/lib/api"
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
  { to: "/explorer", label: "Explorer", icon: MessageSquare },
]

const leadershipLinks: NavItem[] = [
  { to: "/dashboard", label: "Organization", icon: LayoutDashboard },
  { to: "/synthesis", label: "Synthesis", icon: Sparkles },
  { to: "/maturity", label: "AI Maturity", icon: TrendingUp },
  { to: "/finops", label: "FinOps", icon: DollarSign },
  { to: "/quality", label: "Code Quality", icon: GitPullRequest },
  { to: "/friction", label: "Friction", icon: AlertTriangle },
  { to: "/projects", label: "Projects", icon: FolderKanban },
  { to: "/growth", label: "Growth", icon: GraduationCap },
  { to: "/explorer", label: "Explorer", icon: MessageSquare },
  { to: "/sessions", label: "Sessions", icon: MonitorDot },
  { to: "/teams", label: "Teams", icon: Users2 },
  { to: "/engineers", label: "Engineers", icon: Users },
]

const adminLink: NavItem = { to: "/admin", label: "Admin", icon: Settings }

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const { user, logout } = useAuth()
  const { resolved, setTheme } = useTheme()
  const navigate = useNavigate()
  const isApiKeyUser = !user && !!getApiKey()
  const role = user?.role ?? (isApiKeyUser ? "admin" : "engineer")
  const effectiveRole = getEffectiveRole(role)
  const isAdmin = role === "admin" || isApiKeyUser

  const links = effectiveRole === "leadership" ? leadershipLinks : engineerLinks
  const allLinks = isAdmin ? [...links, adminLink] : links

  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  const displayName = user?.display_name ?? user?.name ?? "User"

  // Close user menu on outside click
  useEffect(() => {
    if (!menuOpen) return
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClick)
    return () => document.removeEventListener("mousedown", handleClick)
  }, [menuOpen])

  // Close user menu on Escape
  useEffect(() => {
    if (!menuOpen) return
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMenuOpen(false)
    }
    document.addEventListener("keydown", handleKey)
    return () => document.removeEventListener("keydown", handleKey)
  }, [menuOpen])

  const handleLogout = async () => {
    setMenuOpen(false)
    if (user) {
      await logout()
      window.location.reload()
    } else {
      clearApiKey()
      window.location.reload()
    }
  }

  const toggleTheme = () => {
    setTheme(resolved === "dark" ? "light" : "dark")
  }

  return (
    <aside
      className={cn(
        "flex h-full flex-col border-r border-sidebar-border bg-sidebar transition-all duration-200 ease-out",
        collapsed ? "w-16" : "w-60",
      )}
    >
      {/* Logo area */}
      <div
        className={cn(
          "flex h-12 shrink-0 items-center border-b border-sidebar-border",
          collapsed ? "justify-center px-0" : "justify-between px-4",
        )}
      >
        <div className="flex items-center gap-2 overflow-hidden">
          <img src="/logo-mark.svg" alt="Primer" className="h-5 w-5 shrink-0" />
          {!collapsed && (
            <span className="text-base font-semibold text-sidebar-foreground">Primer</span>
          )}
        </div>
        {!collapsed && (
          <button
            onClick={onToggle}
            className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
            title="Collapse sidebar"
          >
            <PanelLeft className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Expand button when collapsed */}
      {collapsed && (
        <div className="flex shrink-0 justify-center py-2">
          <button
            onClick={onToggle}
            className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
            title="Expand sidebar"
          >
            <PanelLeft className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Navigation */}
      <nav className={cn("flex-1 space-y-1 overflow-y-auto", collapsed ? "px-2 py-2" : "p-3")}>
        {allLinks.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            title={collapsed ? link.label : undefined}
            className={({ isActive }) =>
              cn(
                "flex items-center rounded-md text-sm font-medium transition-colors",
                collapsed ? "justify-center px-0 py-2" : "gap-3 px-3 py-2",
                isActive
                  ? "border-l-3 border-primary bg-primary/8 text-primary font-semibold dark:bg-primary/12"
                  : "border-l-3 border-transparent text-muted-foreground hover:bg-accent hover:text-sidebar-foreground",
              )
            }
          >
            <link.icon className={cn("shrink-0", collapsed ? "h-5 w-5" : "h-4 w-4")} />
            {!collapsed && link.label}
          </NavLink>
        ))}
      </nav>

      {/* Divider */}
      <div className="mx-3 border-t border-sidebar-border" />

      {/* User section */}
      <div className={cn("relative shrink-0", collapsed ? "px-2 py-3" : "px-3 py-3")} ref={menuRef}>
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          className={cn(
            "flex w-full items-center rounded-md transition-colors hover:bg-accent",
            collapsed ? "justify-center p-2" : "gap-3 px-3 py-2",
          )}
          aria-label="User menu"
          aria-expanded={menuOpen}
          aria-haspopup="true"
        >
          {user?.avatar_url ? (
            <img
              src={user.avatar_url}
              alt={displayName}
              className="h-8 w-8 shrink-0 rounded-full"
            />
          ) : (
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-medium text-muted-foreground">
              {displayName.charAt(0).toUpperCase()}
            </div>
          )}
          {!collapsed && (
            <div className="min-w-0 text-left">
              <p className="truncate text-sm font-medium text-sidebar-foreground">{displayName}</p>
              <p className="truncate text-xs text-muted-foreground capitalize">{role}</p>
            </div>
          )}
        </button>

        {/* User menu popover (opens upward) */}
        {menuOpen && (
          <div
            className={cn(
              "absolute z-50 w-56 rounded-lg border border-border bg-card py-1 shadow-elevated animate-fade-in",
              collapsed ? "bottom-0 left-full ml-2" : "bottom-full left-3 mb-2",
            )}
          >
            {/* User info */}
            <div className="border-b border-border px-4 py-3">
              <p className="truncate text-sm font-medium">{displayName}</p>
              {user?.github_username && (
                <p className="truncate text-xs text-muted-foreground">@{user.github_username}</p>
              )}
              {!user?.github_username && user?.email && (
                <p className="truncate text-xs text-muted-foreground">{user.email}</p>
              )}
            </div>

            {/* Menu items */}
            <div className="py-1">
              {user && (
                <button
                  onClick={() => {
                    setMenuOpen(false)
                    navigate("/profile")
                  }}
                  className="flex w-full items-center gap-3 px-4 py-2 text-sm text-foreground hover:bg-accent"
                >
                  <User className="h-4 w-4 text-muted-foreground" />
                  Your profile
                </button>
              )}

              <button
                onClick={() => {
                  toggleTheme()
                  setMenuOpen(false)
                }}
                className="flex w-full items-center gap-3 px-4 py-2 text-sm text-foreground hover:bg-accent"
              >
                {resolved === "dark" ? (
                  <Sun className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <Moon className="h-4 w-4 text-muted-foreground" />
                )}
                {resolved === "dark" ? "Light mode" : "Dark mode"}
              </button>
            </div>

            <div className="border-t border-border py-1">
              <button
                onClick={handleLogout}
                className="flex w-full items-center gap-3 px-4 py-2 text-sm text-foreground hover:bg-accent"
              >
                <LogOut className="h-4 w-4 text-muted-foreground" />
                Sign out
              </button>
            </div>
          </div>
        )}
      </div>
    </aside>
  )
}
