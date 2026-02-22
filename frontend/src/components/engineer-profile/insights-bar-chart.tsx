interface BarItem {
  label: string
  value: number
}

interface InsightsBarChartProps {
  title: string
  items: BarItem[]
  color?: string
}

export function InsightsBarChart({ title, items, color = "#2563eb" }: InsightsBarChartProps) {
  if (items.length === 0) return null

  const maxValue = Math.max(...items.map((i) => i.value))

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </div>
      <div className="space-y-1.5">
        {items.map((item) => (
          <div key={item.label} className="flex items-center gap-2">
            <span className="w-24 shrink-0 truncate text-[11px] text-muted-foreground">
              {item.label}
            </span>
            <div className="h-1.5 flex-1 rounded-full bg-muted">
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: maxValue > 0 ? `${(item.value / maxValue) * 100}%` : "0%",
                  backgroundColor: color,
                }}
              />
            </div>
            <span className="w-8 text-right text-[11px] font-medium text-muted-foreground">
              {item.value.toLocaleString()}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
