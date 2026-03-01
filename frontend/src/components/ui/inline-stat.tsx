import type { LucideIcon } from "lucide-react"

interface InlineStatProps {
  label: string
  value: string | number
  icon?: LucideIcon
}

export function InlineStat({ label, value, icon: Icon }: InlineStatProps) {
  return (
    <div className="rounded-xl border border-border/60 bg-card p-3">
      <div className="flex items-center gap-2.5">
        {Icon && (
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/8">
            <Icon className="h-4 w-4 text-primary" />
          </div>
        )}
        <div className="min-w-0">
          <p className="text-2xl font-display leading-tight">{value}</p>
          <p className="text-xs text-muted-foreground">{label}</p>
        </div>
      </div>
    </div>
  )
}
