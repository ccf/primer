import { Inbox } from "lucide-react"

interface EmptyStateProps {
  message?: string
}

export function EmptyState({ message = "No data available" }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <Inbox className="h-10 w-10 text-muted-foreground/50" />
      <p className="mt-3 text-sm text-muted-foreground">{message}</p>
    </div>
  )
}
