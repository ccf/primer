import type { QualityByType } from "@/types/api"

interface Props {
  data: QualityByType[]
}

export function QualityByTypeChart({ data }: Props) {
  if (data.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">
        No session type data available.
      </div>
    )
  }

  const maxCommits = Math.max(...data.map((d) => d.avg_commits), 1)

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <h3 className="mb-4 text-sm font-semibold">Quality by Session Type</h3>
      <div className="space-y-3">
        {data.map((d) => (
          <div key={d.session_type} className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium">{d.session_type}</span>
              <span className="text-muted-foreground">
                {d.session_count} session{d.session_count !== 1 ? "s" : ""} | avg {d.avg_commits.toFixed(1)} commits | +{d.avg_lines_added.toFixed(0)} / -{d.avg_lines_deleted.toFixed(0)} lines
              </span>
            </div>
            <div className="h-3 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary"
                style={{ width: `${(d.avg_commits / maxCommits) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
