import { useState, useRef, useEffect } from "react"
import { DayPicker } from "react-day-picker"
import { format } from "date-fns"
import { Calendar } from "lucide-react"
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
  const [showCalendar, setShowCalendar] = useState(false)
  const [selected, setSelected] = useState<{ from?: Date; to?: Date }>({})
  const popoverRef = useRef<HTMLDivElement>(null)

  // Close popover on outside click
  useEffect(() => {
    if (!showCalendar) return
    function handleClick(e: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setShowCalendar(false)
      }
    }
    document.addEventListener("mousedown", handleClick)
    return () => document.removeEventListener("mousedown", handleClick)
  }, [showCalendar])

  const handleDayPickerSelect = (range: { from?: Date; to?: Date } | undefined) => {
    if (!range) return
    setSelected(range)
    if (range.from && range.to) {
      const label = `${format(range.from, "MMM d")} – ${format(range.to, "MMM d")}`
      onChange({
        startDate: range.from.toISOString(),
        endDate: range.to.toISOString(),
        label,
      })
      setShowCalendar(false)
    }
  }

  const isCustom = value != null && !presets.some((p) => p.label === value.label)

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
      <div className="relative" ref={popoverRef}>
        <button
          onClick={() => setShowCalendar(!showCalendar)}
          className={cn(
            "flex h-7 items-center gap-1 rounded-md px-2.5 text-xs font-medium transition-colors",
            isCustom
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
          )}
        >
          <Calendar className="h-3 w-3" />
          {isCustom ? value.label : "Custom"}
        </button>
        {showCalendar && (
          <div className="absolute right-0 top-full z-50 mt-1 rounded-lg border border-border bg-card p-3 shadow-lg">
            <DayPicker
              mode="range"
              selected={selected.from ? { from: selected.from, to: selected.to } : undefined}
              onSelect={handleDayPickerSelect}
              disabled={{ after: new Date() }}
              numberOfMonths={2}
              classNames={{
                root: "text-sm",
                months: "flex gap-4",
                month_caption: "flex justify-center py-1 font-medium",
                nav: "flex items-center justify-between",
                button_previous: "h-7 w-7 rounded-md hover:bg-accent flex items-center justify-center",
                button_next: "h-7 w-7 rounded-md hover:bg-accent flex items-center justify-center",
                weekdays: "flex",
                weekday: "w-8 text-center text-xs text-muted-foreground font-medium",
                week: "flex",
                day: "h-8 w-8 text-center text-sm",
                day_button: "h-8 w-8 rounded-md hover:bg-accent transition-colors",
                selected: "bg-primary text-primary-foreground hover:bg-primary",
                range_middle: "bg-accent text-accent-foreground",
                range_start: "bg-primary text-primary-foreground rounded-l-md",
                range_end: "bg-primary text-primary-foreground rounded-r-md",
                today: "font-bold",
                disabled: "text-muted-foreground/50 pointer-events-none",
              }}
            />
          </div>
        )}
      </div>
    </div>
  )
}
