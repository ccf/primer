import type { QualityOverview } from "@/types/api"

function fmt(n: number | null | undefined, decimals = 1): string {
  if (n == null) return "-"
  return n.toLocaleString(undefined, { maximumFractionDigits: decimals })
}

function pct(n: number | null | undefined): string {
  if (n == null) return "-"
  return `${(n * 100).toFixed(0)}%`
}

interface Props {
  overview: QualityOverview
}

export function QualityOverviewCards({ overview }: Props) {
  const cards = [
    { label: "Total Commits", value: fmt(overview.total_commits, 0) },
    {
      label: "Lines Changed",
      value: `+${fmt(overview.total_lines_added, 0)} / -${fmt(overview.total_lines_deleted, 0)}`,
    },
    { label: "Pull Requests", value: fmt(overview.total_prs, 0) },
    { label: "PR Merge Rate", value: pct(overview.pr_merge_rate) },
    {
      label: "Avg Time to Merge",
      value: overview.avg_time_to_merge_hours != null
        ? `${fmt(overview.avg_time_to_merge_hours)}h`
        : "-",
    },
  ]

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      {cards.map((card) => (
        <div
          key={card.label}
          className="rounded-lg border border-border bg-card p-4"
        >
          <p className="text-xs font-medium text-muted-foreground">{card.label}</p>
          <p className="mt-1 text-2xl font-bold">{card.value}</p>
        </div>
      ))}
    </div>
  )
}
