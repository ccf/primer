import { Inbox } from "lucide-react"

interface EmptyStateProps {
  message?: string
}

export function EmptyState({ message = "No data available" }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="rounded-2xl bg-muted/50 p-4">
        <Inbox className="h-8 w-8 text-muted-foreground/40" />
      </div>
      <p className="mt-4 text-sm text-muted-foreground">{message}</p>
    </div>
  )
}
