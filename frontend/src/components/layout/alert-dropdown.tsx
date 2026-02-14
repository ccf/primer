import { Check, X } from "lucide-react"
import { formatDistanceToNow, parseISO } from "date-fns"
import { Badge } from "@/components/ui/badge"
import { useAcknowledgeAlert, useDismissAlert } from "@/hooks/use-api-mutations"
import type { AlertResponse } from "@/types/api"

interface AlertDropdownProps {
  alerts: AlertResponse[]
  onClose: () => void
}

const severityVariant: Record<string, "destructive" | "warning" | "secondary"> = {
  critical: "destructive",
  warning: "warning",
  info: "secondary",
}

export function AlertDropdown({ alerts, onClose }: AlertDropdownProps) {
  const ack = useAcknowledgeAlert()
  const dismiss = useDismissAlert()

  return (
    <div className="absolute right-0 top-10 z-50 w-80 rounded-lg border border-border bg-card shadow-lg">
      <div className="flex items-center justify-between border-b border-border px-4 py-2">
        <span className="text-sm font-semibold">Alerts</span>
        <button
          onClick={onClose}
          className="text-muted-foreground hover:text-foreground"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="max-h-80 overflow-y-auto">
        {alerts.length === 0 ? (
          <p className="px-4 py-6 text-center text-sm text-muted-foreground">
            No alerts
          </p>
        ) : (
          alerts.map((alert) => (
            <div
              key={alert.id}
              className="border-b border-border px-4 py-3 last:border-0"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <Badge variant={severityVariant[alert.severity] ?? "secondary"}>
                      {alert.severity}
                    </Badge>
                    <span className="truncate text-xs text-muted-foreground">
                      {formatDistanceToNow(parseISO(alert.detected_at), {
                        addSuffix: true,
                      })}
                    </span>
                  </div>
                  <p className="mt-1 text-sm font-medium">{alert.title}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {alert.message}
                  </p>
                </div>
                <div className="flex gap-1">
                  {!alert.acknowledged_at && (
                    <button
                      onClick={() => ack.mutate(alert.id)}
                      className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground hover:bg-accent hover:text-foreground"
                      title="Acknowledge"
                    >
                      <Check className="h-3.5 w-3.5" />
                    </button>
                  )}
                  <button
                    onClick={() => dismiss.mutate(alert.id)}
                    className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground hover:bg-accent hover:text-foreground"
                    title="Dismiss"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
