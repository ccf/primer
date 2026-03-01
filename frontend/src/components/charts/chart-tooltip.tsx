interface Payload {
  dataKey?: string | number
  name?: string
  value?: number
  color?: string
}

interface ChartTooltipProps {
  active?: boolean
  payload?: Payload[]
  label?: string
  formatter?: (value: number) => string
}

export function ChartTooltip({ active, payload, label, formatter }: ChartTooltipProps) {
  if (!active || !payload?.length) return null

  return (
    <div className="rounded-xl border border-border/60 bg-card px-3 py-2.5 shadow-elevated">
      {label && (
        <p className="mb-1.5 text-xs font-medium text-muted-foreground">{label}</p>
      )}
      <div className="space-y-1">
        {payload.map((entry) => (
          <div key={String(entry.dataKey)} className="flex items-center gap-2">
            <span
              className="h-2.5 w-2.5 shrink-0 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-xs text-muted-foreground capitalize">
              {entry.name ?? String(entry.dataKey)}
            </span>
            <span className="ml-auto font-display text-sm">
              {formatter && typeof entry.value === "number"
                ? formatter(entry.value)
                : entry.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
