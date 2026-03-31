import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useCreateDeviceToken, useRevokeDeviceToken } from "@/hooks/use-api-mutations"
import { useDeviceTokens } from "@/hooks/use-api-queries"

export function DeviceTokenCard() {
  const { data: tokens, isLoading } = useDeviceTokens()
  const createToken = useCreateDeviceToken()
  const revokeToken = useRevokeDeviceToken()
  const [latestRawToken, setLatestRawToken] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const handleCreate = () => {
    createToken.mutate(
      { name: "Local machine" },
      {
        onSuccess: (data) => {
          setLatestRawToken(data.raw_token)
          setCopied(false)
        },
      },
    )
  }

  const handleCopy = async () => {
    if (!latestRawToken) return
    await navigator.clipboard.writeText(latestRawToken)
    setCopied(true)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Local Device Tokens</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Use a device token for hooks and the sidecar. It is scoped to your local machine and is a
          better fit than a long-lived engineer API key.
        </p>

        <div className="flex flex-wrap items-center gap-2">
          <Button onClick={handleCreate} disabled={createToken.isPending}>
            Create device token
          </Button>
          {createToken.isPending && (
            <span className="text-sm text-muted-foreground">Creating token…</span>
          )}
        </div>

        {latestRawToken && (
          <div className="rounded-xl border border-border/60 bg-muted/20 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Copy now
            </p>
            <p className="mt-2 break-all font-mono text-sm">{latestRawToken}</p>
            <div className="mt-3 flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={handleCopy}>
                {copied ? "Copied" : "Copy token"}
              </Button>
              <span className="text-xs text-muted-foreground">
                You will not be able to see this raw token again.
              </span>
            </div>
          </div>
        )}

        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading tokens…</p>
        ) : !tokens || tokens.length === 0 ? (
          <p className="text-sm text-muted-foreground">No device tokens yet.</p>
        ) : (
          <div className="space-y-3">
            {tokens.map((token) => (
              <div
                key={token.id}
                className="flex flex-col gap-3 rounded-xl border border-border/60 bg-background/70 p-4 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-medium">{token.name}</p>
                    {token.revoked && <Badge variant="outline">Revoked</Badge>}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Ends with {token.token_last_four} • Created{" "}
                    {new Date(token.created_at).toLocaleDateString()}
                  </p>
                </div>
                {!token.revoked && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => revokeToken.mutate(token.id)}
                    disabled={revokeToken.isPending}
                  >
                    Revoke
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
