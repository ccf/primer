import type { LucideIcon } from "lucide-react"
import { Inbox } from "lucide-react"
import { Link } from "react-router-dom"

interface EmptyStateProps {
  message?: string
  title?: string
  description?: string
  icon?: LucideIcon
  actionLabel?: string
  actionHref?: string
}

export function EmptyState({
  message,
  title,
  description,
  icon: Icon = Inbox,
  actionLabel,
  actionHref,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="rounded-2xl bg-muted/50 p-4">
        <Icon className="h-8 w-8 text-muted-foreground/40" />
      </div>
      {title && <h3 className="mt-4 text-sm font-medium text-foreground">{title}</h3>}
      {(message || description) && (
        <p className="mt-2 max-w-sm text-sm text-muted-foreground">
          {description ?? message ?? "No data available"}
        </p>
      )}
      {!title && !message && !description && (
        <p className="mt-4 text-sm text-muted-foreground">No data available</p>
      )}
      {actionLabel && actionHref && (
        <Link
          to={actionHref}
          className="mt-4 text-sm font-medium text-primary hover:underline"
        >
          {actionLabel}
        </Link>
      )}
    </div>
  )
}
