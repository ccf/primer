import { cn } from "@/lib/utils"

export interface DateRange {
  startDate: string
  endDate: string
  label: string
}

interface DateRangePickerProps {
  value: DateRange | null
  onChange: (range: DateRange | null) => void
}

function daysAgo(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() - days)
  return d.toISOString()
}

function now(): string {
  return new Date().toISOString()
}

const presets: { label: string; days: number }[] = [
  { label: "7d", days: 7 },
  { label: "30d", days: 30 },
  { label: "90d", days: 90 },
  { label: "1y", days: 365 },
]

export function DateRangePicker({ value, onChange }: DateRangePickerProps) {
  return (
    <div className="flex items-center gap-1">
      <button
        onClick={() => onChange(null)}
        className={cn(
          "h-7 rounded-md px-2.5 text-xs font-medium transition-colors",
          value === null
            ? "bg-primary text-primary-foreground"
            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
        )}
      >
        All
      </button>
      {presets.map((p) => (
        <button
          key={p.label}
          onClick={() =>
            onChange({ startDate: daysAgo(p.days), endDate: now(), label: p.label })
          }
          className={cn(
            "h-7 rounded-md px-2.5 text-xs font-medium transition-colors",
            value?.label === p.label
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
          )}
        >
          {p.label}
        </button>
      ))}
    </div>
  )
}
