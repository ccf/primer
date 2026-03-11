import { UserRoundSearch } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { EngineerResponse } from "@/types/api"

interface EngineerChooserCardProps {
  title: string
  description: string
  engineers: EngineerResponse[]
  onSelect: (engineerId: string) => void
  emptyMessage?: string
}

export function EngineerChooserCard({
  title,
  description,
  engineers,
  onSelect,
  emptyMessage = "No active engineers are available.",
}: EngineerChooserCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <UserRoundSearch className="h-4 w-4" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground">{description}</p>

        {engineers.length === 0 ? (
          <p className="text-sm text-muted-foreground">{emptyMessage}</p>
        ) : (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {engineers.map((engineer) => (
              <button
                key={engineer.id}
                type="button"
                onClick={() => onSelect(engineer.id)}
                className="rounded-xl border border-border/60 bg-card p-4 text-left transition-colors hover:bg-accent hover:text-accent-foreground"
              >
                <p className="font-medium">{engineer.display_name ?? engineer.name}</p>
                <p className="mt-1 text-sm text-muted-foreground">{engineer.email}</p>
              </button>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
