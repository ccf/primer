import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from "react"
import type { AuthUser } from "@/types/auth"
import { clearApiKey } from "@/lib/api"

interface AuthContextValue {
  user: AuthUser | null
  loading: boolean
  login: () => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  login: async () => {},
  logout: async () => {},
})

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  return useContext(AuthContext)
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  // On mount: try to restore session from cookie
  useEffect(() => {
    fetch("/api/v1/auth/me", { credentials: "include" })
      .then((res) => {
        if (res.ok) return res.json()
        return null
      })
      .then((data) => {
        if (data) {
          setUser({
            engineer_id: data.id,
            name: data.name,
            email: data.email,
            role: data.role,
            team_id: data.team_id,
            avatar_url: data.avatar_url,
            github_username: data.github_username,
            display_name: data.display_name,
          })
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async () => {
    const res = await fetch("/api/v1/auth/github/login")
    if (!res.ok) throw new Error("Failed to initiate login")
    const { url, state } = await res.json()
    sessionStorage.setItem("primer_oauth_state", state)
    window.location.href = url
  }, [])

  const logout = useCallback(async () => {
    await fetch("/api/v1/auth/logout", {
      method: "POST",
      credentials: "include",
    }).catch(() => {})
    clearApiKey()
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
