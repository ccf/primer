import { useState, useRef, useEffect } from "react"
import { Bell } from "lucide-react"
import { useAlerts } from "@/hooks/use-api-queries"
import { AlertDropdown } from "./alert-dropdown"

export function AlertBell() {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const { data: alerts } = useAlerts(false)

  const unacknowledged = alerts?.filter((a) => !a.acknowledged_at) ?? []
  const count = unacknowledged.length

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClick)
    return () => document.removeEventListener("mousedown", handleClick)
  }, [])

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground"
        title="Alerts"
      >
        <Bell className="h-4 w-4" />
        {count > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-bold text-destructive-foreground">
            {count > 99 ? "99+" : count}
          </span>
        )}
      </button>
      {open && (
        <AlertDropdown alerts={alerts ?? []} onClose={() => setOpen(false)} />
      )}
    </div>
  )
}
