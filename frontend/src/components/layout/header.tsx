import { useState, useRef, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import type { TeamResponse } from "@/types/api"
import { useTeams } from "@/hooks/use-api-queries"
import { useAuth } from "@/lib/auth-context"
import { useTheme } from "@/lib/theme-context"
import { clearApiKey, getApiKey } from "@/lib/api"
import { getEffectiveRole } from "@/lib/role-utils"
import { LogOut, Sun, Moon, User } from "lucide-react"
import { DateRangePicker, type DateRange } from "./date-range-picker"
import { AlertBell } from "./alert-bell"

interface HeaderProps {
  teamId: string | null
  onTeamChange: (id: string | null) => void
  dateRange: DateRange | null
  onDateRangeChange: (range: DateRange | null) => void
}

export function Header({ teamId, onTeamChange, dateRange, onDateRangeChange }: HeaderProps) {
  const { data: teams } = useTeams()
  const { user, logout } = useAuth()
  const { resolved, setTheme } = useTheme()
  const isApiKeyUser = !user && !!getApiKey()
  const role = user?.role ?? (isApiKeyUser ? "admin" : "engineer")
  const showTeamFilter = getEffectiveRole(role) === "leadership"
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  // Close menu on outside click
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

  // Close menu on Escape
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

  const displayName = user?.display_name ?? user?.name ?? "User"

  return (
    <header className="flex h-12 items-center justify-between border-b border-border bg-card px-6">
      <div />
      <div className="flex items-center gap-3">
        {showTeamFilter && (
          <select
            value={teamId ?? ""}
            onChange={(e) => onTeamChange(e.target.value || null)}
            className="h-8 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
          >
            <option value="">All teams</option>
            {teams?.map((t: TeamResponse) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        )}

        <DateRangePicker value={dateRange} onChange={onDateRangeChange} />

        <AlertBell />

        {/* Avatar dropdown */}
        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="flex h-8 w-8 items-center justify-center rounded-full ring-2 ring-transparent hover:ring-border transition-shadow"
            aria-label="User menu"
            aria-expanded={menuOpen}
            aria-haspopup="true"
          >
            {user?.avatar_url ? (
              <img
                src={user.avatar_url}
                alt={displayName}
                className="h-8 w-8 rounded-full"
              />
            ) : (
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-xs font-medium">
                {displayName.charAt(0).toUpperCase()}
              </div>
            )}
          </button>

          {menuOpen && (
            <div className="absolute right-0 top-full z-50 mt-1 w-56 rounded-lg border border-border bg-card py-1 shadow-lg">
              {/* User info */}
              <div className="border-b border-border px-4 py-3">
                <p className="truncate text-sm font-medium">{displayName}</p>
                {user?.github_username && (
                  <p className="truncate text-xs text-muted-foreground">
                    @{user.github_username}
                  </p>
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
      </div>
    </header>
  )
}
