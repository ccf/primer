import { Card, CardContent } from "@/components/ui/card"
import { GitPullRequest, CheckCircle2 } from "lucide-react"

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
          <p className="mt-4 text-sm font-medium">No quality data</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Connect a GitHub App to enable PR tracking and code quality metrics.
          </p>
        </CardContent>
      </Card>
    )
  }

  if (quality.no_data_yet) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-16">
          <div className="rounded-lg bg-emerald-500/10 p-3">
            <CheckCircle2 className="h-8 w-8 text-emerald-600 dark:text-emerald-400" />
          </div>
          <p className="mt-4 text-sm font-medium">GitHub connected</p>
          <p className="mt-1 text-xs text-muted-foreground">
            No commits or PRs linked to sessions yet. Quality metrics will appear as you work.
          </p>
        </CardContent>
      </Card>
    )
  }

  const display = Object.entries(quality).filter(
    ([key]) => key !== "github_connected" && key !== "no_data_yet",
  )

  return (
    <Card>
      <CardContent className="p-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {display.map(([key, value]) => (
            <div key={key}>
              <p className="text-xs text-muted-foreground">{key.replace(/_/g, " ")}</p>
              <p className="mt-1 text-sm font-medium">
                {value == null ? "—" : String(value)}
              </p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
