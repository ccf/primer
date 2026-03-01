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
    <div className="relative flex min-h-screen items-center justify-center bg-background p-4 overflow-hidden">
      {/* Background decorations */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute top-1/4 left-1/3 h-[600px] w-[600px] rounded-full bg-primary/[0.04] blur-3xl" />
        <div className="absolute bottom-1/4 right-1/3 h-[400px] w-[400px] rounded-full bg-primary/[0.06] blur-3xl" />
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage:
              "radial-gradient(circle, currentColor 1px, transparent 1px)",
            backgroundSize: "24px 24px",
          }}
        />
      </div>

      <div className="relative animate-fade-in">
        <Card className="w-full max-w-sm">
          <CardHeader className="text-center">
            <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10">
              <img src="/logo-mark.svg" alt="Primer" className="h-8 w-8" />
            </div>
            <CardTitle className="font-display text-2xl">Primer</CardTitle>
            <CardDescription>Sign in to view your AI coding insights</CardDescription>
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
              className="flex w-full items-center justify-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Use Admin API Key
              {showApiKey ? (
                <ChevronUp className="h-3 w-3" />
              ) : (
                <ChevronDown className="h-3 w-3" />
              )}
            </button>

            {showApiKey && (
              <form onSubmit={handleApiKeySubmit} className="space-y-3 animate-slide-up">
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
                    className="h-9 w-full rounded-md border border-input bg-background pl-10 pr-3 text-sm font-mono focus:outline-none focus:ring-1 focus:ring-ring transition-colors"
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

        <p className="mt-6 text-center text-xs text-muted-foreground/50">
          Open source &middot; Self-hosted &middot; Privacy-first
        </p>
      </div>
    </div>
  )
}
