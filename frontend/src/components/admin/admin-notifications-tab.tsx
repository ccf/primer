import { useState } from "react"
import { Bell, CheckCircle2, XCircle } from "lucide-react"
import { useSlackConfig } from "@/hooks/use-api-queries"
import { useTestSlack } from "@/hooks/use-api-mutations"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { TableSkeleton } from "@/components/shared/loading-skeleton"

export function AdminNotificationsTab() {
  const { data: config, isLoading } = useSlackConfig()
  const testSlack = useTestSlack()
  const [testResult, setTestResult] = useState<{ success: boolean; error?: string } | null>(null)

  const handleTest = () => {
    setTestResult(null)
    testSlack.mutate(undefined, {
      onSuccess: (data) => setTestResult(data),
      onError: (err) => setTestResult({ success: false, error: String(err) }),
    })
  }

  if (isLoading) return <TableSkeleton rows={3} />

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm font-medium">
            <Bell className="h-4 w-4" />
            Slack Integration
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg border border-border p-3">
              <p className="text-xs text-muted-foreground">Webhook URL</p>
              <p className="mt-1 text-sm font-medium">
                {config?.webhook_url_set ? (
                  <span className="inline-flex items-center gap-1 text-green-600 dark:text-green-400">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Configured
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-muted-foreground">
                    <XCircle className="h-3.5 w-3.5" /> Not configured
                  </span>
                )}
              </p>
            </div>
            <div className="rounded-lg border border-border p-3">
              <p className="text-xs text-muted-foreground">Alerts Enabled</p>
              <p className="mt-1 text-sm font-medium">
                {config?.enabled ? (
                  <span className="inline-flex items-center gap-1 text-green-600 dark:text-green-400">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Enabled
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-muted-foreground">
                    <XCircle className="h-3.5 w-3.5" /> Disabled
                  </span>
                )}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button
              size="sm"
              onClick={handleTest}
              disabled={!config?.webhook_url_set || testSlack.isPending}
            >
              {testSlack.isPending ? "Sending..." : "Test Slack"}
            </Button>
            {testResult && (
              <span
                className={`text-sm ${testResult.success ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}`}
              >
                {testResult.success ? "Test message sent!" : `Failed: ${testResult.error}`}
              </span>
            )}
          </div>

          <div className="rounded-lg bg-muted/50 p-3 text-xs text-muted-foreground">
            <p className="font-medium">Configuration</p>
            <p className="mt-1">
              Set <code className="rounded bg-muted px-1 py-0.5">PRIMER_SLACK_WEBHOOK_URL</code> to
              your Slack incoming webhook URL, and{" "}
              <code className="rounded bg-muted px-1 py-0.5">PRIMER_SLACK_ALERTS_ENABLED=true</code>{" "}
              to enable automatic alert notifications.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
