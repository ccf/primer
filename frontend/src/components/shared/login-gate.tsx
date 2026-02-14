import { useState } from "react"
import { setApiKey } from "@/lib/api"
import { KeyRound } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export function LoginGate() {
  const [key, setKey] = useState("")
  const [error, setError] = useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!key.trim()) {
      setError("Please enter an API key")
      return
    }

    // Test the key
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
          <CardTitle className="text-xl">Primer Dashboard</CardTitle>
          <CardDescription>Enter your admin API key to continue</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
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
                  autoFocus
                />
              </div>
              {error && <p className="mt-1.5 text-sm text-destructive">{error}</p>}
            </div>
            <Button type="submit" className="w-full">
              Sign in
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
