import { Link } from "react-router-dom"
import { AlertTriangle, CheckCircle2, ArrowRight } from "lucide-react"
import { formatDistanceToNow, parseISO } from "date-fns"
import { Badge } from "@/components/ui/badge"
import { useAlerts } from "@/hooks/use-api-queries"

const severityVariant: Record<string, "destructive" | "warning" | "secondary"> = {
  critical: "destructive",
  warning: "warning",
  info: "secondary",
}

export function AttentionSection() {
  const { data: alerts } = useAlerts(false)

  const activeAlerts = alerts?.filter((a) => !a.dismissed).slice(0, 5) ?? []

  if (activeAlerts.length === 0) {
    return (
      <div className="flex items-center gap-3 rounded-lg border border-border bg-card p-4">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-emerald-500/10">
          <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
        </div>
        <div>
          <p className="text-sm font-medium">All clear</p>
          <p className="text-xs text-muted-foreground">No active alerts or anomalies</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-amber-500" />
          <h2 className="text-sm font-semibold">Needs Attention</h2>
        </div>
        <Link
          to="/admin?tab=alerts"
          className="flex items-center gap-1 text-xs font-medium text-primary hover:underline"
        >
          View all <ArrowRight className="h-3 w-3" />
        </Link>
      </div>
      <div className="space-y-1.5">
        {activeAlerts.map((alert) => (
          <div
            key={alert.id}
            className="flex items-start gap-3 rounded-lg border border-border bg-card px-4 py-3"
          >
            <Badge variant={severityVariant[alert.severity] ?? "secondary"} className="mt-0.5 shrink-0">
              {alert.severity}
            </Badge>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">{alert.title}</p>
              <p className="text-xs text-muted-foreground">{alert.message}</p>
            </div>
            <span className="shrink-0 text-xs text-muted-foreground">
              {formatDistanceToNow(parseISO(alert.detected_at), { addSuffix: true })}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
