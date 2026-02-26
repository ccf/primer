import { useState } from "react"
import { setApiKey } from "@/lib/api"
import { useAuth } from "@/lib/auth-context"
import { Github, KeyRound, ChevronDown, ChevronUp } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export function LoginPage() {
  const { login } = useAuth()
  const [showApiKey, setShowApiKey] = useState(false)
  const [key, setKey] = useState("")
  const [error, setError] = useState("")
  const [loginLoading, setLoginLoading] = useState(false)

  const handleGithubLogin = async () => {
    setLoginLoading(true)
    try {
      await login()
    } catch {
      setError("Failed to initiate GitHub login")
      setLoginLoading(false)
    }
  }

  const handleApiKeySubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!key.trim()) {
      setError("Please enter an API key")
      return
    }
    try {
      const res = await fetch("/api/v1/teams", {
        headers: { "x-admin-key": key.trim() },
      })
      if (res.ok) {
        setApiKey(key.trim())
        window.location.reload()
      } else {
        setError("Invalid API key")
      }
    } catch {
      setError("Cannot connect to server")
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <img src="/logo-mark.svg" alt="Primer" className="h-7 w-7" />
          </div>
          <CardTitle className="text-xl">Primer</CardTitle>
          <CardDescription>Sign in to view your Claude Code insights</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button
            className="w-full"
            onClick={handleGithubLogin}
            disabled={loginLoading}
          >
            <Github className="mr-2 h-4 w-4" />
            {loginLoading ? "Redirecting..." : "Sign in with GitHub"}
          </Button>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-card px-2 text-muted-foreground">or</span>
            </div>
          </div>

          <button
            type="button"
            onClick={() => setShowApiKey(!showApiKey)}
            className="flex w-full items-center justify-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            Use Admin API Key
            {showApiKey ? (
              <ChevronUp className="h-3 w-3" />
            ) : (
              <ChevronDown className="h-3 w-3" />
            )}
          </button>

          {showApiKey && (
            <form onSubmit={handleApiKeySubmit} className="space-y-3">
              <div className="relative">
                <KeyRound className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="password"
                  value={key}
                  onChange={(e) => {
                    setKey(e.target.value)
                    setError("")
                  }}
                  placeholder="primer-admin-dev-key"
                  className="h-9 w-full rounded-md border border-input bg-background pl-10 pr-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
              <Button type="submit" variant="outline" className="w-full">
                Sign in with API Key
              </Button>
            </form>
          )}

          {error && <p className="text-center text-sm text-destructive">{error}</p>}
        </CardContent>
      </Card>
    </div>
  )
}
