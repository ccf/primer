import type { FindingsOverview } from "@/types/api"

function fmt(n: number | null | undefined, decimals = 1): string {
  if (n == null) return "-"
  return n.toLocaleString(undefined, { maximumFractionDigits: decimals })
}

function pct(n: number | null | undefined): string {
  if (n == null) return "-"
  return `${(n * 100).toFixed(0)}%`
}

const SEVERITY_COLORS: Record<string, string> = {
  high: "bg-red-500",
  medium: "bg-amber-500",
  low: "bg-blue-500",
  info: "bg-gray-400",
}

interface Props {
  findings: FindingsOverview
}

export function FindingsOverviewSection({ findings }: Props) {
  const total = findings.total_findings

  const cards = [
    { label: "Total Findings", value: fmt(total, 0) },
    { label: "Fix Rate", value: pct(findings.fix_rate) },
    { label: "Avg per PR", value: fmt(findings.avg_findings_per_pr) },
  ]

  const severityOrder = ["high", "medium", "low", "info"]
  const orderedSeverities = severityOrder.filter((s) => findings.by_severity[s])

  return (
    <section className="space-y-4">
      <h2 className="text-sm font-semibold text-muted-foreground">
        Automated Review Findings
      </h2>

      <div className="grid gap-4 sm:grid-cols-3">
        {cards.map((card) => (
          <div
            key={card.label}
            className="rounded-lg border border-border bg-card p-4"
          >
            <p className="text-xs font-medium text-muted-foreground">
              {card.label}
            </p>
            <p className="mt-1 text-2xl font-bold">{card.value}</p>
          </div>
        ))}
      </div>

      {orderedSeverities.length > 0 && (
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="mb-3 text-xs font-medium text-muted-foreground">
            Severity Breakdown
          </p>
          <div className="flex h-4 w-full overflow-hidden rounded-full bg-muted">
            {orderedSeverities.map((severity) => {
              const count = findings.by_severity[severity]
              const widthPct = total > 0 ? (count / total) * 100 : 0
              return (
                <div
                  key={severity}
                  className={`${SEVERITY_COLORS[severity] || "bg-gray-400"}`}
                  style={{ width: `${widthPct}%` }}
                  title={`${severity}: ${count}`}
                />
              )
            })}
          </div>
          <div className="mt-2 flex flex-wrap gap-4 text-xs text-muted-foreground">
            {orderedSeverities.map((severity) => (
              <span key={severity} className="flex items-center gap-1.5">
                <span
                  className={`inline-block h-2 w-2 rounded-full ${SEVERITY_COLORS[severity] || "bg-gray-400"}`}
                />
                {severity}: {findings.by_severity[severity]}
              </span>
            ))}
          </div>
        </div>
      )}

      {Object.keys(findings.by_source).length > 1 && (
        <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
          {Object.entries(findings.by_source).map(([source, count]) => (
            <span
              key={source}
              className="rounded-full border border-border px-2.5 py-0.5"
            >
              {source}: {count}
            </span>
          ))}
        </div>
      )}
    </section>
  )
}
