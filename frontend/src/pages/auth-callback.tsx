import { useEffect, useState } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { BarChart3, Loader2 } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export function AuthCallbackPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [error, setError] = useState("")

  useEffect(() => {
    const code = searchParams.get("code")
    const state = searchParams.get("state")
    const savedState = sessionStorage.getItem("primer_oauth_state")

    if (!code || !state) {
      setError("Missing authorization code or state")
      return
    }

    if (state !== savedState) {
      setError("Invalid OAuth state — possible CSRF attack")
      return
    }

    sessionStorage.removeItem("primer_oauth_state")

    fetch("/api/v1/auth/github/callback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ code, state }),
    })
      .then((res) => {
        if (!res.ok) throw new Error("Authentication failed")
        return res.json()
      })
      .then(() => {
        // Cookies are set by the response. Navigate home and reload to pick up the auth state.
        window.location.href = "/"
      })
      .catch((err) => {
        setError(err.message || "Authentication failed")
      })
  }, [searchParams, navigate])

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <BarChart3 className="h-6 w-6 text-primary" />
          </div>
          <CardTitle className="text-xl">
            {error ? "Authentication Failed" : "Signing in..."}
          </CardTitle>
        </CardHeader>
        <CardContent className="text-center">
          {error ? (
            <div className="space-y-3">
              <p className="text-sm text-destructive">{error}</p>
              <a href="/" className="text-sm text-primary hover:underline">
                Return to login
              </a>
            </div>
          ) : (
            <Loader2 className="mx-auto h-6 w-6 animate-spin text-muted-foreground" />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
