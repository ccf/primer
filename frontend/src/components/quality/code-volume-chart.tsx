import type { DailyCodeVolume } from "@/types/api"

interface Props {
  data: DailyCodeVolume[]
}

export function CodeVolumeChart({ data }: Props) {
  if (data.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">
        No code volume data available.
      </div>
    )
  }

  const maxVal = Math.max(...data.map((d) => Math.max(d.lines_added, d.lines_deleted)), 1)

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <h3 className="mb-4 text-sm font-semibold">Daily Code Volume</h3>
      <div className="space-y-2">
        {data.slice(-30).map((d) => (
          <div key={d.date} className="flex items-center gap-3 text-xs">
            <span className="w-20 shrink-0 text-muted-foreground">{d.date.slice(5)}</span>
            <div className="flex flex-1 gap-1">
              <div
                className="h-4 rounded-sm bg-emerald-500"
                style={{ width: `${(d.lines_added / maxVal) * 100}%` }}
                title={`+${d.lines_added} added`}
              />
              <div
                className="h-4 rounded-sm bg-red-500"
                style={{ width: `${(d.lines_deleted / maxVal) * 100}%` }}
                title={`-${d.lines_deleted} deleted`}
              />
            </div>
            <span className="w-16 shrink-0 text-right text-muted-foreground">
              {d.commits} commit{d.commits !== 1 ? "s" : ""}
            </span>
          </div>
        ))}
      </div>
      <div className="mt-3 flex gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-sm bg-emerald-500" /> Added
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-sm bg-red-500" /> Deleted
        </span>
      </div>
    </div>
  )
}
