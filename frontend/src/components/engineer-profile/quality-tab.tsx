import { Card, CardContent } from "@/components/ui/card"
import { GitPullRequest } from "lucide-react"

interface QualityTabProps {
  quality: Record<string, unknown>
}

export function QualityTab({ quality }: QualityTabProps) {
  const hasData = Object.keys(quality).length > 0

  if (!hasData) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-16">
          <div className="rounded-lg bg-muted p-3">
            <GitPullRequest className="h-8 w-8 text-muted-foreground" />
          </div>
          <p className="mt-4 text-sm font-medium">Coming soon</p>
          <p className="mt-1 text-xs text-muted-foreground">
            PR tracking required to display quality metrics.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardContent className="p-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Object.entries(quality).map(([key, value]) => (
            <div key={key}>
              <p className="text-xs text-muted-foreground">{key.replace(/_/g, " ")}</p>
              <p className="mt-1 text-sm font-medium">{String(value)}</p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
